// Watchlist Widget Component
// Uses BaseListWidget from ui/widgets.js

(function() {
    const { BaseListWidget } = window.VibeBaseWidgets;

    const component = {
        components: { BaseListWidget },
        template: `
            <div class="h-full flex flex-col">
                <BaseListWidget :data="stocks" :columns="columns" />
                <div class="mt-1 text-[10px] text-slate-600 text-right pr-2">
                    Updated: {{ lastUpdate }}
                </div>
            </div>
        `,
                    props: ['widgetId', 'moduleId', 'config'],
                setup(props) {
                    const { ref, onMounted, onUnmounted, watch } = Vue;
                    const stocks = ref([]);
                    const lastUpdate = ref('-');
        
                    const getChangeColor = (val, row) => {
                        if (val > 0) return 'text-red-400 font-bold';
                        if (val < 0) return 'text-emerald-400 font-bold';
                        return 'text-slate-400';
                    };
        
                    const columns = [
                        { key: 'code', label: 'Code', class: 'font-mono text-slate-300' },
                        { key: 'name', label: 'Name', class: 'text-slate-200' },
                        { key: 'price', label: 'Price', class: 'text-right font-mono text-yellow-300', format: (v) => v ? v.toFixed(2) : '-' },
                        { 
                            key: 'change', 
                            label: 'Change %', 
                            class: getChangeColor,
                            format: (v) => v ? `${v > 0 ? '+' : ''}${v}%` : '-' 
                        }
                    ];
        
                    const handleUpdate = (data) => {
                        stocks.value = data;
                        lastUpdate.value = new Date().toLocaleTimeString();
                    };
                    
                                const subscribe = () => {
                                    if (window.vibeSocket) {
                                        window.vibeSocket.subscribe(props.widgetId, handleUpdate);
                                        // Send Subscribe Command with Config
                                        const sendSub = () => {
                                            window.vibeSocket.send('subscribe', {
                                                widgetId: props.widgetId,
                                                moduleId: props.moduleId,
                                                config: props.config || {}
                                            });
                                        };
                                        
                                        sendSub();
                                        // Retry once after 2 seconds in case backend module wasn't ready
                                        setTimeout(sendSub, 2000);
                                    }
                                };        
                    onMounted(() => {
                        subscribe();
                        // If socket reconnects, we might need to resubscribe. 
                        // Currently vibeSocket implementation in index.html doesn't auto-replay sends on reconnect.
                        // Assuming connection is stable for now.
                    });
        
                    onUnmounted(() => {
                        if (window.vibeSocket) {
                            window.vibeSocket.unsubscribe(props.widgetId);
                        }
                    });
        
                    return {
                        stocks,
                        lastUpdate,
                        columns
                    };
                }
            };
            window.VibeComponentRegistry = window.VibeComponentRegistry || {};
    window.VibeComponentRegistry['watchlist-widget'] = component;
})();
