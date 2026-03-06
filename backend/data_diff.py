import hashlib
import json
from typing import Dict, List, Any, Union


class DataDiff:
    @staticmethod
    def _row_hash(row: Dict[str, Any]) -> str:
        serialized = json.dumps(row, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    @staticmethod
    def _make_row_key(row: Dict[str, Any], pk_cols: List[str]) -> str:
        key_parts = [str(row.get(col, "")) for col in pk_cols]
        return "||".join(key_parts)

    @staticmethod
    def compare_data(
        source_data: List[Dict], target_data: List[Dict], pk_cols: List[str]
    ) -> Dict[str, Any]:
        if not pk_cols:
            return {"error": "No primary key found"}

        source_map = {DataDiff._make_row_key(
            row, pk_cols): row for row in source_data}
        target_map = {DataDiff._make_row_key(
            row, pk_cols): row for row in target_data}

        added = []
        modified = []
        removed = []

        for key, s_row in source_map.items():
            if key not in target_map:
                added.append(s_row)
            else:
                t_row = target_map[key]
                if DataDiff._row_hash(s_row) != DataDiff._row_hash(t_row):
                    all_fields = []
                    changed_count = 0
                    for field in s_row.keys():
                        old_val = t_row.get(field)
                        new_val = s_row.get(field)

                        # 精确比较：考虑类型和值
                        if old_val is None and new_val is None:
                            is_changed = False
                        elif old_val is None or new_val is None:
                            is_changed = True
                        elif type(old_val) != type(new_val):
                            is_changed = str(old_val) != str(new_val)
                        else:
                            is_changed = old_val != new_val

                        all_fields.append(
                            {
                                "field": field,
                                "oldValue": str(old_val)
                                if old_val is not None
                                else "NULL",
                                "newValue": str(new_val)
                                if new_val is not None
                                else "NULL",
                                "changed": is_changed,
                            }
                        )

                        if is_changed:
                            changed_count += 1

                    modified.append(
                        {
                            "source": s_row,
                            "target": t_row,
                            "field_comparison": all_fields,
                            "changed_count": changed_count,
                        }
                    )

        for key, t_row in target_map.items():
            if key not in source_map:
                removed.append(t_row)

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "total_source": len(source_data),
            "total_target": len(target_data),
        }
