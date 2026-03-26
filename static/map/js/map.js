// 骑砍英雄传 - 地图 JavaScript

const { createApp } = Vue;

createApp({
    data() {
        return {
            // 地图数据
            locations: [],
            
            // 玩家数据
            playerName: '',
            playerLevel: 1,
            playerX: 500,
            playerY: 500,
            currentLocation: '',
            
            // 地图交互
            zoom: 1,
            panX: 0,
            panY: 0,
            isPanning: false,
            lastPanX: 0,
            lastPanY: 0,
            
            // 选中地点
            selectedLocation: null,
            
            // 旅行状态
            isTraveling: false,
            travelDestination: '',
            travelProgress: 0,
            travelTargetX: 0,
            travelTargetY: 0,
            
            // WebSocket
            ws: null,
            userId: '',
            token: '',
        };
    },
    
    computed: {
        mapStyle() {
            return {
                transform: `translate(${this.panX}px, ${this.panY}px) scale(${this.zoom})`,
            };
        },
        
        canTravel() {
            if (this.isTraveling || !this.selectedLocation) return false;
            const dist = this.calculateDistance(
                this.playerX, this.playerY,
                this.selectedLocation.x, this.selectedLocation.y
            );
            return dist > 10;
        },
    },
    
    mounted() {
        this.loadMapData();
        this.loadPlayerData();
        this.connectWebSocket();
        this.centerMap();
    },
    
    methods: {
        async loadMapData() {
            try {
                const res = await axios.get('/api/map/locations');
                if (res.data.success) {
                    this.locations = res.data.locations;
                }
            } catch (err) {
                console.error('加载地图数据失败:', err);
            }
        },
        
        async loadPlayerData() {
            try {
                // 从localStorage获取用户信息
                const userData = JSON.parse(localStorage.getItem('qikan_user') || '{}');
                this.userId = userData.user_id || '';
                this.token = userData.token || '';
                
                if (!this.userId) {
                    // 尝试从URL参数获取
                    const params = new URLSearchParams(window.location.search);
                    const key = params.get('key');
                    if (key) {
                        // 尝试解析密钥获取user_id
                        this.userId = key.split('_')[0];
                    }
                }
                
                if (this.userId) {
                    const res = await axios.get(`/api/map/player?user_id=${this.userId}`);
                    if (res.data.success) {
                        const player = res.data.player;
                        this.playerName = player.name;
                        this.playerLevel = player.level;
                        this.playerX = player.x;
                        this.playerY = player.y;
                        this.currentLocation = player.current_location?.name || '流浪中';
                        
                        if (player.travel_destination) {
                            this.isTraveling = true;
                            this.travelDestination = player.travel_destination;
                            this.travelProgress = player.travel_progress;
                        }
                    }
                }
            } catch (err) {
                console.error('加载玩家数据失败:', err);
            }
        },
        
        connectWebSocket() {
            // WebSocket连接将在后续实现
            console.log('地图WebSocket连接待实现');
        },
        
        centerMap() {
            // 将地图居中到玩家位置
            const container = this.$refs.mapCanvas;
            if (container) {
                this.panX = container.clientWidth / 2 - this.playerX * this.zoom;
                this.panY = container.clientHeight / 2 - this.playerY * this.zoom;
            }
        },
        
        getMarkerIcon(type) {
            const icons = {
                'town': '🏰',
                'castle': '⚔️',
                'village': '🏘️',
                'bandit_camp': '⛺',
            };
            return icons[type] || '📍';
        },
        
        selectLocation(loc) {
            this.selectedLocation = loc;
        },
        
        async startTravel() {
            if (!this.selectedLocation || !this.canTravel) return;
            
            try {
                const res = await axios.post('/api/map/travel', {
                    user_id: this.userId,
                    destination: this.selectedLocation.id,
                });
                
                if (res.data.success) {
                    this.isTraveling = true;
                    this.travelDestination = this.selectedLocation.name;
                    this.travelTargetX = this.selectedLocation.x;
                    this.travelTargetY = this.selectedLocation.y;
                    this.travelProgress = 0;
                    
                    // 开始旅行动画
                    this.animateTravel();
                }
            } catch (err) {
                console.error('开始旅行失败:', err);
                alert('开始旅行失败: ' + (err.response?.data?.message || err.message));
            }
        },
        
        animateTravel() {
            if (!this.isTraveling) return;
            
            // 模拟旅行进度
            const interval = setInterval(() => {
                if (!this.isTraveling) {
                    clearInterval(interval);
                    return;
                }
                
                this.travelProgress += 2;
                
                // 更新玩家位置
                const progress = this.travelProgress / 100;
                this.playerX = this.playerX + (this.travelTargetX - this.playerX) * 0.05;
                this.playerY = this.playerY + (this.travelTargetY - this.playerY) * 0.05;
                
                if (this.travelProgress >= 100) {
                    clearInterval(interval);
                    this.completeTravel();
                }
            }, 500);
        },
        
        async completeTravel() {
            this.isTraveling = false;
            this.travelProgress = 100;
            this.playerX = this.travelTargetX;
            this.playerY = this.travelTargetY;
            this.currentLocation = this.travelDestination;
            
            // 通知服务器旅行完成
            try {
                await axios.post('/api/map/arrive', {
                    user_id: this.userId,
                    location: this.selectedLocation?.id,
                });
            } catch (err) {
                console.error('通知服务器旅行完成失败:', err);
            }
        },
        
        // 缩放控制
        zoomIn() {
            this.zoom = Math.min(3, this.zoom + 0.2);
        },
        
        zoomOut() {
            this.zoom = Math.max(0.3, this.zoom - 0.2);
        },
        
        resetView() {
            this.zoom = 1;
            this.centerMap();
        },
        
        handleZoom(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            this.zoom = Math.max(0.3, Math.min(3, this.zoom + delta));
        },
        
        // 平移控制
        startPan(e) {
            this.isPanning = true;
            this.lastPanX = e.clientX;
            this.lastPanY = e.clientY;
        },
        
        doPan(e) {
            if (!this.isPanning) return;
            
            const dx = e.clientX - this.lastPanX;
            const dy = e.clientY - this.lastPanY;
            
            this.panX += dx;
            this.panY += dy;
            
            this.lastPanX = e.clientX;
            this.lastPanY = e.clientY;
        },
        
        endPan() {
            this.isPanning = false;
        },
        
        handleMapClick(e) {
            // 点击地图空白处关闭面板
            if (e.target.classList.contains('map-bg') || e.target.classList.contains('map-content')) {
                this.selectedLocation = null;
            }
        },
        
        // 工具函数
        calculateDistance(x1, y1, x2, y2) {
            return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
        },
    },
}).mount('#app');
