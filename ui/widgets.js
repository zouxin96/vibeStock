// vibeStock Base Widgets Library
(function() {
    const { ref, onMounted, onUnmounted, watch, nextTick } = Vue;

    // --- 1. Base List Widget ---
    const BaseListWidget = {
        props: ['data', 'columns'],
        template: `
            <div class="h-full flex flex-col overflow-hidden">
                <div class="overflow-auto flex-grow custom-scrollbar">
                    <table class="w-full text-sm text-left">
                        <thead class="text-xs text-slate-400 uppercase bg-slate-700/80 sticky top-0 backdrop-blur-sm z-10">
                            <tr>
                                <th v-for="col in columns" :key="col.key" class="px-4 py-2 font-medium tracking-wider">{{ col.label }}</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-700/50">
                            <tr v-for="(row, idx) in data" :key="row.id || idx" class="hover:bg-slate-700/30 transition-colors">
                                <td v-for="col in columns" :key="col.key" :class="['px-4 py-2', getColClass(col, row)]">
                                    <!-- Use slot if available (not easily generic in pure JS obj, using formatter function) -->
                                    <span v-if="!col.format">{{ row[col.key] }}</span>
                                    <span v-else v-html="col.format(row[col.key], row)"></span>
                                </td>
                            </tr>
                            <tr v-if="!data || data.length === 0">
                                <td :colspan="columns.length" class="text-center py-8 text-slate-500 italic">
                                    No Data Available
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `,
        setup(props) {
            const getColClass = (col, row) => {
                if (typeof col.class === 'function') return col.class(row[col.key], row);
                return col.class || '';
            };
            return { getColClass };
        }
    };

    // --- 2. Base ECharts Widget (Internal) ---
    const BaseChartWidget = {
        props: ['options', 'theme'],
        template: `<div ref="chartDom" class="w-full h-full min-h-[200px]"></div>`,
        setup(props) {
            const chartDom = ref(null);
            let chartInstance = null;

            const initChart = () => {
                if (!chartDom.value) return;
                chartInstance = echarts.init(chartDom.value, props.theme || 'dark', { renderer: 'canvas' });
                if (props.options) {
                    chartInstance.setOption({
                        backgroundColor: 'transparent',
                        ...props.options
                    });
                }
                window.addEventListener('resize', resizeChart);
            };

            const resizeChart = () => {
                if (chartInstance) chartInstance.resize();
            };

            watch(() => props.options, (newVal) => {
                if (chartInstance && newVal) {
                    chartInstance.setOption(newVal, { notMerge: false, replaceMerge: ['series'] });
                }
            }, { deep: true });

            onMounted(() => {
                nextTick(initChart);
            });

            onUnmounted(() => {
                window.removeEventListener('resize', resizeChart);
                if (chartInstance) chartInstance.dispose();
            });

            return { chartDom };
        }
    };

    // --- 3. Concrete Chart Widgets ---

    // Pie Chart
    const BasePieWidget = {
        components: { BaseChartWidget },
        props: ['data', 'titleKey', 'valueKey', 'chartTitle'],
        template: `
            <BaseChartWidget :options="chartOptions" />
        `,
        setup(props) {
            const chartOptions = ref({});
            
            watch(() => props.data, (newData) => {
                if (!newData) return;
                const seriesData = newData.map(item => ({
                    name: item[props.titleKey || 'name'],
                    value: item[props.valueKey || 'value']
                }));
                
                chartOptions.value = {
                    title: { text: props.chartTitle, left: 'center' },
                    tooltip: { trigger: 'item' },
                    legend: { bottom: '0%', left: 'center' },
                    series: [{
                        type: 'pie',
                        radius: ['40%', '70%'],
                        avoidLabelOverlap: false,
                        itemStyle: { borderRadius: 5, borderColor: '#1e293b', borderWidth: 2 },
                        label: { show: false, position: 'center' },
                        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
                        data: seriesData
                    }]
                };
            }, { immediate: true, deep: true });

            return { chartOptions };
        }
    };

    // Bar Chart
    const BaseBarWidget = {
        components: { BaseChartWidget },
        props: ['data', 'categoryKey', 'valueKey', 'chartTitle'],
        template: `
            <BaseChartWidget :options="chartOptions" />
        `,
        setup(props) {
            const chartOptions = ref({});
            
            watch(() => props.data, (newData) => {
                if (!newData) return;
                const categories = newData.map(item => item[props.categoryKey || 'category']);
                const values = newData.map(item => item[props.valueKey || 'value']);
                
                chartOptions.value = {
                    title: { text: props.chartTitle },
                    tooltip: { trigger: 'axis' },
                    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                    xAxis: { type: 'category', data: categories },
                    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#334155' } } },
                    series: [{
                        data: values,
                        type: 'bar',
                        itemStyle: { borderRadius: [4, 4, 0, 0] }
                    }]
                };
            }, { immediate: true, deep: true });

            return { chartOptions };
        }
    };

    // Line Chart
    const BaseLineWidget = {
        components: { BaseChartWidget },
        props: ['data', 'categoryKey', 'valueKeys', 'chartTitle'], // valueKeys can be array for multiple lines
        template: `
            <BaseChartWidget :options="chartOptions" />
        `,
        setup(props) {
            const chartOptions = ref({});
            
            watch(() => props.data, (newData) => {
                if (!newData) return;
                const categories = newData.map(item => item[props.categoryKey || 'date']);
                
                const series = [];
                const keys = Array.isArray(props.valueKeys) ? props.valueKeys : [props.valueKeys || 'value'];
                
                keys.forEach(key => {
                    series.push({
                        name: key,
                        type: 'line',
                        smooth: true,
                        data: newData.map(item => item[key])
                    });
                });

                chartOptions.value = {
                    title: { text: props.chartTitle },
                    tooltip: { trigger: 'axis' },
                    legend: { data: keys },
                    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                    xAxis: { type: 'category', data: categories, boundaryGap: false },
                    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#334155' } } },
                    series: series
                };
            }, { immediate: true, deep: true });

            return { chartOptions };
        }
    };

    // Candlestick (K-Line) Chart
    const BaseCandleWidget = {
        components: { BaseChartWidget },
        props: ['data', 'chartTitle'], // data: [{date, open, close, low, high}, ...]
        template: `
            <BaseChartWidget :options="chartOptions" />
        `,
        setup(props) {
            const chartOptions = ref({});
            
            watch(() => props.data, (newData) => {
                if (!newData) return;
                // ECharts Candle expects: [open, close, low, high]
                const categoryData = [];
                const values = [];
                
                newData.forEach(item => {
                    categoryData.push(item.date);
                    values.push([item.open, item.close, item.low, item.high]);
                });

                chartOptions.value = {
                    title: { text: props.chartTitle },
                    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
                    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                    xAxis: { type: 'category', data: categoryData, scale: true, boundaryGap: false },
                    yAxis: { scale: true, splitLine: { lineStyle: { color: '#334155' } } },
                    dataZoom: [{ type: 'inside', start: 50, end: 100 }, { show: true, type: 'slider', top: '90%' }],
                    series: [{
                        type: 'candlestick',
                        data: values,
                        itemStyle: {
                            color: '#ef4444', // Rise (Red in CN)
                            color0: '#10b981', // Fall (Green in CN)
                            borderColor: '#ef4444',
                            borderColor0: '#10b981'
                        }
                    }]
                };
            }, { immediate: true, deep: true });

            return { chartOptions };
        }
    };

    // Register globally
    window.VibeBaseWidgets = {
        BaseListWidget,
        BasePieWidget,
        BaseBarWidget,
        BaseLineWidget,
        BaseCandleWidget
    };
})();
