import { ref } from 'vue';

// Event types
export enum GameEvent {
  TOWN_ENTER = 'TOWN_ENTER',
  TOWN_LEAVE = 'TOWN_LEAVE',
  ITEM_ACQUIRE = 'ITEM_ACQUIRE',
}

// Item type definition
export interface Item {
  id: string;
  name: string;
  description?: string;
  quantity?: number;
}

// Game state management - Singleton pattern
class GameStateImpl {
  private town = ref<string | null>(null);
  private inventory = ref<Item[]>([]);
  private subscribers: ((event: { type: GameEvent; payload: any }) => void)[] = [];

  get currentTown() {
    return this.town.value;
  }

  get inventoryItems() {
    return this.inventory.value;
  }

  // Event system
  subscribe(callback: (event: { type: GameEvent; payload: any }) => void) {
    this.subscribers.push(callback);
    return () => this.unsubscribe(callback);
  }

  unsubscribe(callback: (event: { type: GameEvent; payload: any }) => void) {
    this.subscribers = this.subscribers.filter(cb => cb !== callback);
  }

  // Town management
  enterTown(townName: string) {
    this.town.value = townName;
    this.dispatch({ type: GameEvent.TOWN_ENTER, payload: { townName } });
  }

  leaveTown() {
    const previousTown = this.town.value;
    this.town.value = null;
    this.dispatch({ type: GameEvent.TOWN_LEAVE, payload: { townName: previousTown } });
  }

  // Inventory management
  addItem(item: Item) {
    this.inventory.value = [...this.inventory.value, item];
    this.dispatch({ type: GameEvent.ITEM_ACQUIRE, payload: { item } });
  }

  // Event dispatching
  private dispatch(event: { type: GameEvent; payload: any }) {
    this.subscribers.forEach(callback => callback(event));
  }
}

// Singleton instance
let gameStateInstance: GameStateImpl | null = null;

export function getGameState(): GameStateImpl {
  if (!gameStateInstance) {
    gameStateInstance = new GameStateImpl();
  }
  return gameStateInstance;
}