from typing import Dict, List, Any


class SchemaDiff:
    @staticmethod
    def compare_columns(
        source_cols: List[Dict], target_cols: List[Dict]
    ) -> Dict[str, List]:
        source_map = {col["Field"]: col for col in source_cols}
        target_map = {col["Field"]: col for col in target_cols}

        added = [col for name, col in source_map.items() if name not in target_map]
        removed = [col for name, col in target_map.items() if name not in source_map]
        modified = []

        for name in set(source_map.keys()) & set(target_map.keys()):
            s_col, t_col = source_map[name], target_map[name]
            if (
                s_col["Type"] != t_col["Type"]
                or s_col["Null"] != t_col["Null"]
                or s_col["Default"] != t_col["Default"]
            ):
                modified.append({"source": s_col, "target": t_col})

        return {"added": added, "removed": removed, "modified": modified}

    @staticmethod
    def compare_indexes(
        source_idx: List[Dict], target_idx: List[Dict]
    ) -> Dict[str, List]:
        source_map = {}
        for idx in source_idx:
            key = idx["Key_name"]
            if key not in source_map:
                source_map[key] = []
            source_map[key].append(idx)

        target_map = {}
        for idx in target_idx:
            key = idx["Key_name"]
            if key not in target_map:
                target_map[key] = []
            target_map[key].append(idx)

        added = [key for key in source_map if key not in target_map]
        removed = [key for key in target_map if key not in source_map]

        return {"added": added, "removed": removed}

    @staticmethod
    def compare_tables(
        source_tables: List[str], target_tables: List[str]
    ) -> Dict[str, List]:
        source_set = set(source_tables)
        target_set = set(target_tables)

        return {
            "added": list(source_set - target_set),
            "removed": list(target_set - source_set),
            "common": list(source_set & target_set),
        }
