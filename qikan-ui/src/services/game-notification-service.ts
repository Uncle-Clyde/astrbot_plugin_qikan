import { ElNotification } from 'element-plus';
import { GameEvent, getGameState } from '@/game/game-state';

// Notification service for game events
export class GameNotificationService {
  private static instance: GameNotificationService;
  private gameState: ReturnType<typeof getGameState>;

  private constructor() {
    this.gameState = getGameState();
    this.initEventListeners();
  }

  static getInstance(): GameNotificationService {
    if (!GameNotificationService.instance) {
      GameNotificationService.instance = new GameNotificationService();
    }
    return GameNotificationService.instance;
  }

  private initEventListeners() {
    this.gameState.subscribe(this.handleGameEvent.bind(this));
  }

  private handleGameEvent(event: { type: GameEvent; payload: any }) {
    switch (event.type) {
      case GameEvent.TOWN_ENTER:
        this.showTownEnterNotification(event.payload.townName);
        break;
      case GameEvent.TOWN_LEAVE:
        this.showTownLeaveNotification(event.payload.townName);
        break;
      case GameEvent.ITEM_ACQUIRE:
        this.showItemAcquireNotification(event.payload.item);
        break;
    }
  }

  private showTownEnterNotification(townName: string) {
    ElNotification({
      title: 'Town Entry',
      message: `You have entered ${townName}`,
      duration: 5000,
      type: 'success',
      position: 'top-right'
    });
  }

  private showTownLeaveNotification(townName: string) {
    ElNotification({
      title: 'Town Exit',
      message: `You have left ${townName}`,
      duration: 5000,
      type: 'warning',
      position: 'top-right'
    });
  }

  private showItemAcquireNotification(item: { name: string; quantity?: number }) {
    const message = quantity
      ? `Acquired ${quantity}x ${item.name}`
      : `Acquired ${item.name}`;

    ElNotification({
      title: 'Item Acquired',
      message,
      duration: 5000,
      type: 'success',
      position: 'top-right'
    });
  }
}

// Initialize the service
GameNotificationService.getInstance();