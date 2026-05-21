// VIOLATION: domain imports infrastructure
import { persist } from '../db/session';
export class Order { save() { return persist(this); } }
