(function() {
    const { BaseDataWidget } = window.VibeBaseWidgets;

    const AKShareMonitorWidget = {
        components: { 'base-data-widget': BaseDataWidget },
        props: ['widgetId'], 
        setup(props) {
            const { ref, onMounted, onUnmounted } = Vue;
            const status = ref({ is_connected: false, last_updated: '-', error_count: 0 });
            
            onMounted(() => {
                if (window.vibeSocket) {
                    window.vibeSocket.subscribe("akshare_status", (data) => {
                        status.value = data;
                    });
                }
            });
            
            onUnmounted(() => {
                if (window.vibeSocket) {
                    window.vibeSocket.unsubscribe("akshare_status");
                }
            });

            return { status };
        },
        template: `
            <div class="h-full w-full">
                <base-data-widget :status="status" title="AKShare Source" />
            </div>
        `
    };

    if (!window.VibeComponentRegistry) {
        window.VibeComponentRegistry = {};
    }
    window.VibeComponentRegistry['akshare-monitor-widget'] = AKShareMonitorWidget;
})();