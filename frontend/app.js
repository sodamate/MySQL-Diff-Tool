const { createApp } = Vue;
const { ElMessage } = ElementPlus;

createApp({
    data() {
        return {
            source: {
                host: 'localhost',
                port: 3306,
                user: 'root',
                password: '',
                database: ''
            },
            target: {
                host: 'localhost',
                port: 3306,
                user: 'root',
                password: '',
                database: ''
            },
            sourceDatabases: [],
            targetDatabases: [],
            sourceTables: [],
            targetTables: [],
            selectedSourceTable: '',
            selectedTargetTable: '',
            compareMode: 'table',
            compareData: true,
            dataLimit: 10000,
            loading: false,
            activeModified: 0,
            currentPageAdded: 1,
            currentPageRemoved: 1,
            currentPageModified: 1,
            pageSizeAdded: 50,
            pageSizeRemoved: 50,
            pageSizeModified: 20,
            result: null,
            schemaResult: null,
            selectedSchemaTable: null,
            schemaSearchSource: '',
            schemaSearchTarget: '',
            svgWidth: 0,
            svgHeight: 0,
            connectionLines: [],
            scrollDebounceTimer: null,
        };
    },
    methods: {
        saveConfig() {
            const config = {
                source: this.source,
                target: this.target,
                compareMode: this.compareMode,
                compareData: this.compareData,
                dataLimit: this.dataLimit
            };
            localStorage.setItem('mysql-diff-config', JSON.stringify(config));
        },
        loadConfig() {
            try {
                const saved = localStorage.getItem('mysql-diff-config');
                if (saved) {
                    const config = JSON.parse(saved);
                    this.source = config.source || this.source;
                    this.target = config.target || this.target;
                    this.compareMode = config.compareMode || this.compareMode;
                    this.compareData = config.compareData !== undefined ? config.compareData : this.compareData;
                    this.dataLimit = config.dataLimit || this.dataLimit;
                    ElMessage.success('已恢复上次连接配置');
                }
            } catch (e) {
                console.error('加载配置失败:', e);
            }
        },
        clearConfig() {
            localStorage.removeItem('mysql-diff-config');
            this.source = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
            this.target = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
            this.sourceDatabases = [];
            this.targetDatabases = [];
            this.sourceTables = [];
            this.targetTables = [];
            ElMessage.success('配置已清除');
        },
        getTableColumns(data) {
            if (!data || data.length === 0) return {};
            return data[0] || {};
        },
        getChangedFieldsCount(item) {
            return item.changed_count || 0;
        },
        getFieldComparison(item) {
            return item.field_comparison || [];
        },
        getPaginatedAdded() {
            if (!this.result?.table_details?.data?.added) return [];
            const start = (this.currentPageAdded - 1) * this.pageSizeAdded;
            const end = start + this.pageSizeAdded;
            return this.result.table_details.data.added.slice(start, end);
        },
        getPaginatedRemoved() {
            if (!this.result?.table_details?.data?.removed) return [];
            const start = (this.currentPageRemoved - 1) * this.pageSizeRemoved;
            const end = start + this.pageSizeRemoved;
            return this.result.table_details.data.removed.slice(start, end);
        },
        getPaginatedModified() {
            if (!this.result?.table_details?.data?.modified) return [];
            const start = (this.currentPageModified - 1) * this.pageSizeModified;
            const end = start + this.pageSizeModified;
            return this.result.table_details.data.modified.slice(start, end);
        },
        async loadSourceDatabases() {
            if (this.sourceDatabases.length > 0) return;
            try {
                const response = await fetch('/api/get-databases', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        host: this.source.host,
                        port: this.source.port,
                        user: this.source.user,
                        password: this.source.password
                    })
                });
const data = await response.json();
                if (response.ok) {
                    this.sourceDatabases = data.databases;
                    ElMessage.success(`源数据库：已加载 ${data.databases.length} 个数据库`);
                } else {
                    ElMessage.error(`获取数据库列表失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`连接错误: ${error.message}`);
            }
        },
        async loadTargetDatabases() {
            if (this.targetDatabases.length > 0) return;
            try {
                const response = await fetch('/api/get-databases', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        host: this.target.host,
                        port: this.target.port,
                        user: this.target.user,
                        password: this.target.password
                    })
                });
                const data = await response.json();
                if (response.ok) {
                    this.targetDatabases = data.databases;
                    ElMessage.success(`目标数据库：已加载 ${data.databases.length} 个数据库`);
                } else {
                    ElMessage.error(`获取数据库列表失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`连接错误: ${error.message}`);
            }
        },
        async loadSourceTables() {
            if (!this.source.database) {
                ElMessage.warning('请先选择数据库');
                return;
            }
            try {
                const response = await fetch('/api/get-tables', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.source)
                });
                const data = await response.json();
                if (response.ok) {
                    this.sourceTables = data.tables;
                    ElMessage.success(`源数据库：共 ${data.tables.length} 个表`);
                } else {
                    ElMessage.error(`获取表列表失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`连接错误: ${error.message}`);
            }
        },
        async loadTargetTables() {
            if (!this.target.database) {
                ElMessage.warning('请先选择数据库');
                return;
            }
            try {
                const response = await fetch('/api/get-tables', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.target)
                });
                const data = await response.json();
                if (response.ok) {
                    this.targetTables = data.tables;
                    ElMessage.success(`目标数据库：共 ${data.tables.length} 个表`);
                } else {
                    ElMessage.error(`获取表列表失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`连接错误: ${error.message}`);
            }
        },
        async compareTable() {
            if (!this.selectedSourceTable || !this.selectedTargetTable) {
                ElMessage.warning('请选择源表和目标表');
                return;
            }
            this.loading = true;
            this.result = null;
            try {
                const response = await fetch('/api/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: this.source,
                        target: this.target,
                        source_table: this.selectedSourceTable,
                        target_table: this.selectedTargetTable,
                        compare_data: this.compareData,
                        data_limit: this.dataLimit
                    })
                });
                const data = await response.json();
                if (response.ok) {
                    this.result = data;
                    ElMessage.success('对比完成！');
                } else {
                    ElMessage.error(`对比失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`对比错误: ${error.message}`);
            } finally {
                this.loading = false;
            }
        },
async compareSchema() {
            this.loading = true;
            this.schemaResult = null;
            this.result = null;
            try {
                const response = await fetch('/api/compare-schema', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: this.source,
                        target: this.target,
                        source_table: '',
                        target_table: '',
                        compare_data: false,
                        data_limit: 0
                    })
                });
                const data = await response.json();
                if (response.ok) {
                    this.schemaResult = data;
                    ElMessage.success('整库对比完成！');
                    // 延迟绘制连线，等待DOM渲染
                    setTimeout(() => this.updateConnectionLines(), 300);
                } else {
                    ElMessage.error(`对比失败: ${data.detail}`);
                }
            } catch (error) {
                ElMessage.error(`对比错误: ${error.message}`);
            } finally {
                this.loading = false;
            }
        },
        downloadSQL() {
            const sql = this.result.sync_sql.join('\n\n');
            const blob = new Blob([sql], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `sync_${this.result.source_table}_${Date.now()}.sql`;
            a.click();
            URL.revokeObjectURL(url);
        },
        downloadSchemaSQL() {
            const sql = this.schemaResult.sync_sql.join('\n');
            const blob = new Blob([sql], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `schema_sync_${Date.now()}.sql`;
            a.click();
            URL.revokeObjectURL(url);
        },
        selectSchemaTable(table) {
            this.selectedSchemaTable = table;
        },
        getFilteredTables(tables, searchText) {
            if (!searchText) return tables;
            return tables.filter(t => t.toLowerCase().includes(searchText.toLowerCase()));
        },
        handleSchemaResize() {
            if (this.scrollDebounceTimer) {
                cancelAnimationFrame(this.scrollDebounceTimer);
            }
            this.scrollDebounceTimer = requestAnimationFrame(() => {
                this.updateConnectionLines();
            });
        },
        updateConnectionLines() {
            if (!this.schemaResult || !this.schemaResult.table_diff) return;

            const leftPanel = this.$refs.leftSchemaPanel;
            const rightPanel = this.$refs.rightSchemaPanel;
            const container = this.$refs.schemaContainer;

            if (!leftPanel || !rightPanel || !container) return;

            const containerRect = container.getBoundingClientRect();
            const lines = [];
            const commonTables = this.schemaResult.table_diff.common || [];

            commonTables.forEach(table => {
                const leftEl = leftPanel.querySelector(`[data-table-name="${table}"][data-panel-side="left"]`);
                const rightEl = rightPanel.querySelector(`[data-table-name="${table}"][data-panel-side="right"]`);

                if (leftEl && rightEl) {
                    const leftRect = leftEl.getBoundingClientRect();
                    const rightRect = rightEl.getBoundingClientRect();

                    // 相对于容器的坐标
                    const x1 = leftRect.right - containerRect.left;
                    const y1 = leftRect.top - containerRect.top + leftRect.height / 2;
                    const x2 = rightRect.left - containerRect.left;
                    const y2 = rightRect.top - containerRect.top + rightRect.height / 2;

                    // 贝塞尔曲线
                    const midX = (x1 + x2) / 2;
                    const pathData = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;

                    const hasChanges = !!this.schemaResult.table_details[table];
                    lines.push({
                        path: pathData,
                        color: hasChanges ? '#E6A23C' : '#67C23A',
                        hasArrow: hasChanges
                    });
                }
            });

            this.connectionLines = lines;
        }
    }, 
    mounted() {
        this.loadConfig();
        window.addEventListener('resize', this.handleSchemaResize);
    },
    watch: {
        source: {
            handler() { this.saveConfig(); },
            deep: true
        },
        target: {
            handler() { this.saveConfig(); },
            deep: true
        },
        compareMode() { this.saveConfig(); },
        compareData() { this.saveConfig(); },
        dataLimit() { this.saveConfig(); }
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.handleSchemaResize);
        if (this.scrollDebounceTimer) {
            cancelAnimationFrame(this.scrollDebounceTimer);
        }
    },
}).use(ElementPlus).mount('#app');