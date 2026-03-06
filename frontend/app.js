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
      configName: '',
      savedConfigs: [],
      saveConfigDebounceTimer: null,
    };
  },
  methods: {
    // 获取所有已保存的配置
    async getSavedConfigs() {
      try {
        const response = await fetch('/api/configs');
        const data = await response.json();
        if (data.success) {
          this.savedConfigs = data.configs;
          return data.configs;
        }
        this.savedConfigs = [];
        return [];
      } catch (error) {
        console.error('获取配置列表失败:', error);
        ElMessage.error('获取配置列表失败');
        this.savedConfigs = [];
        return [];
      }
    },
    // 新建配置
    newConfig() {
      this.source = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
      this.target = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
      this.selectedSourceTable = '';
      this.selectedTargetTable = '';
      this.sourceDatabases = [];
      this.targetDatabases = [];
      this.sourceTables = [];
      this.targetTables = [];
      this.configName = '';
      ElMessage.success('已创建新配置');
    },
    // 保存配置（防抖）
    async saveConfig() {
      // 清除之前的定时器
      if (this.saveConfigDebounceTimer) {
        clearTimeout(this.saveConfigDebounceTimer);
      }
      
      // 设置新的定时器，延迟 500ms 执行保存
      this.saveConfigDebounceTimer = setTimeout(async () => {
        const config = {
          name: 'last-connection',
          source: this.source,
          target: this.target,
          selectedSourceTable: this.selectedSourceTable,
          selectedTargetTable: this.selectedTargetTable,
          compareMode: this.compareMode,
          compareData: this.compareData,
          dataLimit: this.dataLimit
        };
        try {
          const response = await fetch('/api/last-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
          });
          const data = await response.json();
          if (!data.success) {
            console.error('保存配置失败:', data.detail);
          }
        } catch (error) {
          console.error('保存配置失败:', error);
        }
      }, 500);
    },
    // 另存为配置
    async saveAsConfig() {
      if (!this.configName.trim()) {
        ElMessage.warning('请输入配置名称');
        return;
      }

      const configData = {
        name: this.configName.trim(),
        source: this.source,
        target: this.target,
        selectedSourceTable: this.selectedSourceTable,
        selectedTargetTable: this.selectedTargetTable,
        compareMode: this.compareMode,
        compareData: this.compareData,
        dataLimit: this.dataLimit,
        createdAt: new Date().toISOString()
      };

      try {
        // 检查配置是否已存在
        const savedConfigs = this.savedConfigs;
        const existingIndex = savedConfigs.findIndex(config => config.name === configData.name);

        if (existingIndex !== -1) {
          if (!confirm('配置已存在，是否覆盖？')) {
            return;
          }
        }

        const response = await fetch('/api/configs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(configData)
        });

        const data = await response.json();
        if (data.success) {
          ElMessage.success(data.message);
          this.getSavedConfigs(); // 刷新配置列表
        } else {
          ElMessage.error(data.detail || '保存配置失败');
        }
      } catch (error) {
        console.error('保存配置失败:', error);
        ElMessage.error('保存配置失败');
      }
    },
    // 加载配置
    async loadConfig() {
      try {
        const response = await fetch('/api/last-config');
        const data = await response.json();
        if (data.success && data.config) {
          const config = data.config;
          this.source = config.source || this.source;
          this.target = config.target || this.target;
          this.selectedSourceTable = config.selectedSourceTable || this.selectedSourceTable;
          this.selectedTargetTable = config.selectedTargetTable || this.selectedTargetTable;
          this.compareMode = config.compareMode || this.compareMode;
          this.compareData = config.compareData !== undefined ? config.compareData : this.compareData;
          this.dataLimit = config.dataLimit || this.dataLimit;
          ElMessage.success('已恢复上次连接配置');
        }
      } catch (e) {
        console.error('加载配置失败:', e);
      }
    },
    // 加载指定配置
    async loadSpecificConfig(config) {
      console.log('配置数据:', config); // 调试输出
      this.source = config.source;
      this.target = config.target;
      this.selectedSourceTable = config.selectedSourceTable || '';
      this.selectedTargetTable = config.selectedTargetTable || '';
      this.compareMode = config.compareMode || 'table';
      this.compareData = config.compareData !== undefined ? config.compareData : true;
      this.dataLimit = config.dataLimit || 10000;
      this.configName = config.name;
      ElMessage.success(`已加载配置 "${config.name}"`);
    },
    // 删除配置
    async deleteConfig(name) {
      if (confirm(`确定要删除配置 "${name}" 吗？`)) {
        try {
          const response = await fetch(`/api/configs/${name}`, {
            method: 'DELETE'
          });

          const data = await response.json();
          if (data.success) {
            ElMessage.success(data.message);
            this.getSavedConfigs(); // 刷新配置列表
          } else {
            ElMessage.error(data.detail || '删除配置失败');
          }
        } catch (error) {
          console.error('删除配置失败:', error);
          ElMessage.error('删除配置失败');
        }
      }
    },
    // 清除配置
    async clearConfig() {
      try {
        const response = await fetch('/api/last-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'last-connection',
            source: { host: 'localhost', port: 3306, user: 'root', password: '', database: '' },
            target: { host: 'localhost', port: 3306, user: 'root', password: '', database: '' },
            selectedSourceTable: '',
            selectedTargetTable: '',
            compareMode: 'table',
            compareData: true,
            dataLimit: 10000
          })
        });
        
        if (response.ok) {
          this.source = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
          this.target = { host: 'localhost', port: 3306, user: 'root', password: '', database: '' };
          this.selectedSourceTable = '';
          this.selectedTargetTable = '';
          this.sourceDatabases = [];
          this.targetDatabases = [];
          this.sourceTables = [];
          this.targetTables = [];
          this.configName = '';
          ElMessage.success('配置已清除');
        }
      } catch (error) {
        console.error('清除配置失败:', error);
        ElMessage.error('清除配置失败');
      }
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
    // 处理配置命令
    async handleConfigCommand(config) {
      console.log('加载配置:', config); // 调试输出
      await this.loadSpecificConfig(config);
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
    this.getSavedConfigs(); // 加载已保存的配置列表
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
    selectedSourceTable() { this.saveConfig(); },
    selectedTargetTable() { this.saveConfig(); },
    compareMode() { this.saveConfig(); },
    compareData() { this.saveConfig(); },
    dataLimit() { this.saveConfig(); }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleSchemaResize);
    if (this.scrollDebounceTimer) {
      cancelAnimationFrame(this.scrollDebounceTimer);
    }
    if (this.saveConfigDebounceTimer) {
      clearTimeout(this.saveConfigDebounceTimer);
    }
  },
}).use(ElementPlus).mount('#app');