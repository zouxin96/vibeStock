(function() {
    const { ref, onMounted, onUnmounted } = Vue;

    // Check dependency
    if (!window.VibeBaseWidgets || !window.VibeBaseWidgets.BasePieWidget) {
        console.error("[RegionPie] BasePieWidget not found.");
        return;
    }
    const { BasePieWidget } = window.VibeBaseWidgets;

    const RegionPieWidget = {
        components: { BasePieWidget },
        props: ['widgetId', 'moduleId', 'config'],
        template: `
            <div class="h-full flex flex-col bg-slate-900 rounded">
                 <BasePieWidget 
                    :data="pieData" 
                    titleKey="name" 
                    valueKey="value" 
                    chartTitle="" 
                 />
            </div>
        `,
        setup(props) {
            const pieData = ref([]);

            onMounted(() => {
                if (window.vibeSocket) {
                    window.vibeSocket.subscribe("widget_region_pie", (data) => {
                        // console.log("Region Pie Data:", data);
                        pieData.value = data;
                    });
                }
            });

            onUnmounted(() => {
                if (window.vibeSocket) {
                    window.vibeSocket.unsubscribe("widget_region_pie");
                }
            });

            return { pieData };
        }
    };

    if (!window.VibeComponentRegistry) window.VibeComponentRegistry = {};
    window.VibeComponentRegistry['region-pie-widget'] = RegionPieWidget;
    console.log("[RegionPie] Widget registered.");
})();
