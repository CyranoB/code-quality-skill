import { Order } from '../domain/order';
export function handler() { return new Order().save(); }
