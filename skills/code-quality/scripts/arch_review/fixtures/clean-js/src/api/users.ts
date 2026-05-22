import { fetchUser } from '../services/userService';
export function getUser(id: number) { return fetchUser(id); }
