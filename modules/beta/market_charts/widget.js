// Market Charts Widgets
// Requires base widgets from VibeBaseWidgets

(function() {
    const { BasePieWidget, BaseLineWidget, BaseCandleWidget } = window.VibeBaseWidgets;

    // 1. Sector Pie Widget
    const SectorPieComponent = {
        components: { BasePieWidget },
        template: `
            <div class="h-full flex flex-col">
                <BasePieWidget 
                    :data="chartData" 
                    title-key="name" 
                    value-key="value" 
                />
            </div>
        `,
        props: ['widgetId'],
        setup(props) {
            const { ref, onMounted, onUnmounted } = Vue;
            const chartData = ref([]);

            const handleUpdate = (data) => {
                chartData.value = data;
            };

            onMounted(() => {
                if(window.vibeSocket) window.vibeSocket.subscribe(props.widgetId, handleUpdate);
            });
            onUnmounted(() => {
                if(window.vibeSocket) window.vibeSocket.unsubscribe(props.widgetId);
            });
            return { chartData };
        }
    };

    // 2. Index Line Widget
    const IndexLineComponent = {
        components: { BaseLineWidget },
        template: `
            <div class="h-full flex flex-col">
                <BaseLineWidget 
                    :data="chartData" 
                    category-key="time" 
                    value-keys="value" 
                />
            </div>
        `,
        props: ['widgetId'],
        setup(props) {
            const { ref, onMounted, onUnmounted } = Vue;
            const chartData = ref([]);

            const handleUpdate = (data) => {
                chartData.value = data;
            };

            onMounted(() => {
                if(window.vibeSocket) window.vibeSocket.subscribe(props.widgetId, handleUpdate);
            });
            onUnmounted(() => {
                if(window.vibeSocket) window.vibeSocket.unsubscribe(props.widgetId);
            });
            return { chartData };
        }
    };

    // 3. Stock K-Line Widget
    const StockKlineComponent = {
        components: { BaseCandleWidget },
        template: `
            <div class="h-full flex flex-col">
                <BaseCandleWidget 
                    :data="chartData" 
                />
            </div>
        `,
        props: ['widgetId'],
        setup(props) {
            const { ref, onMounted, onUnmounted } = Vue;
            const chartData = ref([]);

            const handleUpdate = (data) => {
                chartData.value = data;
            };

            onMounted(() => {
                if(window.vibeSocket) window.vibeSocket.subscribe(props.widgetId, handleUpdate);
            });
            onUnmounted(() => {
                if(window.vibeSocket) window.vibeSocket.unsubscribe(props.widgetId);
            });
            return { chartData };
        }
    };

    // Register all
    window.VibeComponentRegistry = window.VibeComponentRegistry || {};
    window.VibeComponentRegistry['sector-pie-widget'] = SectorPieComponent;
    window.VibeComponentRegistry['index-line-widget'] = IndexLineComponent;
    window.VibeComponentRegistry['stock-kline-widget'] = StockKlineComponent;

})();
