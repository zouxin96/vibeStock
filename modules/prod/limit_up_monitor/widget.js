const LimitUpMonitorWidget = {
    props: ['id'],
    template: `
    <div class="card h-100">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span>涨停监控服务</span>
            <span class="badge" :class="statusClass">{{ status }}</span>
        </div>
        <div class="card-body">
            <p><strong>上次运行:</strong> {{ lastRun || '等待中...' }}</p>
            <p><strong>抓取数量:</strong> {{ count }}</p>
            <div v-if="topStocks.length > 0">
                <h6 class="mt-3">最新连板前五:</h6>
                <ul class="list-group list-group-flush small">
                    <li v-for="stock in topStocks" class="list-group-item d-flex justify-content-between align-items-center p-1">
                        {{ stock.名称 }}
                        <span class="badge bg-danger rounded-pill">{{ stock.连板数 }}板</span>
                    </li>
                </ul>
            </div>
            <div v-if="error" class="alert alert-danger mt-2 small">
                {{ error }}
            </div>
        </div>
    </div>
    `,
    data() {
        return {
            status: 'Idle',
            lastRun: '',
            count: 0,
            topStocks: [],
            error: null
        }
    },
    computed: {
        statusClass() {
            if (this.status === 'Running') return 'bg-success';
            if (this.status === 'Error') return 'bg-danger';
            return 'bg-secondary';
        }
    },
    mounted() {
        if (window.vibeSocket) {
            window.vibeSocket.subscribe(this.id, (data) => {
                this.lastRun = data.last_run;
                this.status = data.status || 'Running';
                this.count = data.count || 0;
                this.topStocks = data.top_stocks || [];
                this.error = data.error || null;
            });
        }
    }
};

// 注册组件
if (window.VibeComponentRegistry) {
    window.VibeComponentRegistry.register("LimitUpMonitorWidget", LimitUpMonitorWidget);
}
