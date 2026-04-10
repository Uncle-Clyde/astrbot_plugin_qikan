import { ref, onMounted, onBeforeUnmount } from 'vue';

// Game state management
export class GameState {
  private town = ref<string | null>(null);
  private inventory = ref<Item[]>([]);
  private subscribers: ((event: GameEvent) => void)[] = [];

  get currentTown() {
    return this.town.value;
  }

  get inventoryItems() {
    return this.inventory.value;
  }

  // Event system
  subscribe(callback: (event: GameEvent) => void) {
    this.subscribers.push(callback);
    return () => this.unsubscribe(callback);
  }

  unsubscribe(callback: (event: GameEvent) => void) {
    this.subscribers = this.subscribers.filter(cb => cb !== callback);
  }

  // Town management
  enterTown(townName: string) {
    this.town.value = townName;
    this.dispatch({ type: 'TOWN_ENTER', payload: { townName } });
  }

  leaveTown() {
    const previousTown = this.town.value;
    this.town.value = null;
    this.dispatch({ type: 'TOWN_LEAVE', payload: { townName: previousTown } });
  }

  // Inventory management
  addItem(item: Item) {
    this.inventory.value = [...this.inventory.value, item];
    this.dispatch({ type: 'ITEM_ACQUIRE', payload: { item } });
  }

  // Event dispatching
  private dispatch(event: GameEvent) {
    this.subscribers.forEach(callback => callback(event));
  }
}

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