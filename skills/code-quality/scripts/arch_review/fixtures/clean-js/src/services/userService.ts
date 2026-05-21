import { User } from '../domain/user';
export function fetchUser(id: number) { return new User(id); }
