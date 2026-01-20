(function() {
    console.log("[LimitRank] Script execution started.");
    
    try {
        const { ref, computed, onMounted, onUnmounted } = Vue;
        
        const LimitRankWidget = {
            props: ['widgetId', 'moduleId', 'config'],
            template: `
                <div class="h-full flex flex-col bg-slate-900 rounded select-none">
                    <!-- Custom Compact Table -->
                    <div class="flex-grow overflow-auto custom-scrollbar">
                        <table class="w-full text-xs text-left border-collapse">
                            <thead class="text-xs text-slate-400 uppercase bg-slate-800 sticky top-0 z-10">
                                <tr>
                                    <th v-for="col in columns" :key="col.key" 
                                        class="px-2 py-1 font-medium border-b border-slate-700 whitespace-nowrap">
                                        {{ col.label }}
                                    </th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-800">
                                <tr v-for="(row, idx) in paginatedData" :key="row['代码'] || idx" 
                                    class="hover:bg-slate-800/50 transition-colors">
                                    <td v-for="col in columns" :key="col.key" 
                                        :class="['px-2 py-1 border-b border-slate-800/50', getColClass(col, row)]">
                                        <span v-if="!col.format">{{ row[col.key] }}</span>
                                        <span v-else v-html="col.format(row[col.key], row)"></span>
                                    </td>
                                </tr>
                                <tr v-if="paginatedData.length === 0">
                                    <td :colspan="columns.length" class="text-center py-4 text-slate-600 italic">
                                        Waiting for data...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Compact Pagination Footer -->
                    <div class="flex justify-between items-center px-2 py-1 bg-slate-800 border-t border-slate-700 text-xs">
                        <div class="text-slate-400">
                            Total: <span class="text-slate-200">{{ tableData.length }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button @click="prevPage" :disabled="currentPage === 1" 
                                class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-30 rounded text-slate-300">
                                &lt;
                            </button>
                            <span class="text-slate-400 min-w-[30px] text-center">
                                {{ currentPage }}/{{ totalPages }}
                            </span>
                            <button @click="nextPage" :disabled="currentPage === totalPages" 
                                class="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-30 rounded text-slate-300">
                                &gt;
                            </button>
                        </div>
                    </div>
                </div>
            `,
            setup(props) {
                const tableData = ref([]);
                const currentPage = ref(1);
                const pageSize = 8;
                
                const columns = [
                    { key: '名称', label: '名称' },
                    { 
                        key: '最新价', 
                        label: '价格', 
                        format: (val) => `<span class="font-mono text-emerald-400">${Number(val).toFixed(2)}</span>`
                    },
                    { 
                        key: '涨跌幅', 
                        label: '幅度',
                        class: (val) => val > 0 ? 'text-red-500 font-bold' : (val < 0 ? 'text-green-500 font-bold' : 'text-slate-400'),
                        format: (val) => `${Number(val).toFixed(2)}%` 
                    },
                    { 
                        key: '封板资金', 
                        label: '封单(万)',
                        format: (val) => {
                             return `<span class="font-mono text-amber-400">${(Number(val)/10000).toFixed(0)}</span>`;
                        }
                    },
                    { 
                        key: '连板数', 
                        label: '连板',
                        class: 'text-center font-bold text-blue-400'
                    },
                    { key: '所属行业', label: '行业', class: 'text-xs text-slate-400 truncate max-w-[80px]' }
                ];

                const totalPages = computed(() => Math.ceil(tableData.value.length / pageSize) || 1);

                const paginatedData = computed(() => {
                    const start = (currentPage.value - 1) * pageSize;
                    return tableData.value.slice(start, start + pageSize);
                });

                const nextPage = () => {
                    if (currentPage.value < totalPages.value) currentPage.value++;
                };

                const prevPage = () => {
                    if (currentPage.value > 1) currentPage.value--;
                };
                
                const getColClass = (col, row) => {
                    if (typeof col.class === 'function') return col.class(row[col.key], row);
                    return col.class || '';
                };

                onMounted(() => {
                    console.log(`[LimitRank] Component mounted. ID: ${props.widgetId}`);
                    if (window.vibeSocket) {
                        window.vibeSocket.subscribe("widget_limit_rank", (data) => {
                            tableData.value = data;
                            // Reset to page 1 if data refreshes? Maybe keep current page if possible.
                            // But if total pages shrink, adjust.
                            if (currentPage.value > Math.ceil(data.length / pageSize)) {
                                currentPage.value = 1;
                            }
                        });
                    }
                });

                onUnmounted(() => {
                    if (window.vibeSocket) {
                        window.vibeSocket.unsubscribe("widget_limit_rank");
                    }
                });

                return { 
                    tableData, columns, 
                    currentPage, totalPages, paginatedData, 
                    nextPage, prevPage, getColClass 
                };
            }
        };

        if (!window.VibeComponentRegistry) window.VibeComponentRegistry = {};
        window.VibeComponentRegistry['limit-rank-widget'] = LimitRankWidget;
        console.log("[LimitRank] LimitRankWidget successfully registered (Compact Version).");
    } catch (err) {
        console.error("[LimitRank] Script error:", err);
    }
})();
