(function() {
    console.log("[Heatmap] Widget script loading...");
    const { ref, onMounted, onUnmounted } = Vue;

    const MarketHeatmapWidget = {
        props: ['widgetId', 'moduleId', 'config'],
        template: `
            <div class="h-full flex flex-col bg-slate-900/50 p-2 rounded overflow-hidden select-none">
                <!-- Heatmap Grid -->
                <div class="flex-grow flex flex-wrap gap-1 overflow-auto custom-scrollbar content-start">
                    <div v-for="item in heatmapData" :key="item.name"
                         :class="['h-16 rounded flex flex-col justify-center items-center transition-all hover:scale-[1.02] cursor-default relative overflow-hidden', getBgColor(item.change)]"
                         :style="{ width: getBlockWidth(item.limit_weight) }"
                         :title="getTitle(item)">
                        
                        <!-- Weighted Limit Count Badge (if > 0) -->
                        <div v-if="item.limit_weight > 0" class="absolute top-0 right-0 bg-yellow-400/80 text-black text-[9px] px-1 font-bold rounded-bl">
                            {{ item.limit_weight }}
                        </div>

                        <div class="text-xs font-bold text-white/90 truncate max-w-full px-1">{{ item.name }}</div>
                        <div class="text-sm font-mono font-bold text-white">{{ item.change > 0 ? '+' : '' }}{{ item.change.toFixed(2) }}%</div>
                    </div>
                </div>
                
                <!-- Legend -->
                <div class="mt-2 flex justify-between items-center text-[10px] text-slate-500 border-t border-slate-800 pt-1">
                    <div class="flex gap-2">
                        <span class="flex items-center"><i class="w-2 h-2 bg-red-600 rounded-full mr-1"></i> >2%</span>
                        <span class="flex items-center"><i class="w-2 h-2 bg-red-400 rounded-full mr-1"></i> >0%</span>
                        <span class="flex items-center"><i class="w-2 h-2 bg-green-600 rounded-full mr-1"></i> <0%</span>
                    </div>
                    <div>Sorted by Change | Width = Weighted Limit Count</div>
                </div>
                
                <!-- Empty State -->
                <div v-if="heatmapData.length === 0" class="absolute inset-0 flex items-center justify-center text-slate-600 italic text-sm">
                    Loading industry data...
                </div>
            </div>
        `,
        setup(props) {
            const heatmapData = ref([]);

            const getBgColor = (change) => {
                if (change >= 2) return 'bg-red-700 shadow-inner shadow-red-500/20';
                if (change > 0) return 'bg-red-500/80';
                if (change <= -2) return 'bg-green-700 shadow-inner shadow-green-500/20';
                if (change < 0) return 'bg-green-500/80';
                return 'bg-slate-700';
            };
            
            const getBlockWidth = (weight) => {
                // Base width + width per weight
                const baseWidth = 80; // px
                const widthPerPoint = 20; // px
                
                // Cap at some reasonable max to prevent one block taking entire screen if super hot
                const maxW = 300; 
                
                let w = baseWidth + (weight || 0) * widthPerPoint;
                return Math.min(w, maxW) + 'px';
            };
            
            const getTitle = (item) => {
                return item.name + '\nChange: ' + item.change + '%\nWeighted Limit: ' + item.limit_weight;
            };

            onMounted(() => {
                console.log(`[Heatmap] Widget mounted: ${props.widgetId}`);
                if (window.vibeSocket) {
                    window.vibeSocket.subscribe(props.moduleId, (data) => {
                        heatmapData.value = data;
                    });
                }
            });

            onUnmounted(() => {
                if (window.vibeSocket) {
                    window.vibeSocket.unsubscribe(props.moduleId);
                }
            });

            return { heatmapData, getBgColor, getBlockWidth, getTitle };
        }
    };

    if (!window.VibeComponentRegistry) window.VibeComponentRegistry = {};
    window.VibeComponentRegistry['market-heatmap-widget'] = MarketHeatmapWidget;
    console.log("[Heatmap] Widget registered.");
})();
