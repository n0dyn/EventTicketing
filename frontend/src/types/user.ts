import { Organization } from './organization';
import { Event } from './event';

export enum UserRole {
  ADMIN = 'admin',
  ORGANIZER = 'organizer',
  ATTENDEE = 'attendee'
}

export interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  isActive: boolean;
  isSuperuser: boolean;
  role: UserRole;
  createdAt: string;
  updatedAt: string;
  organizations?: Organization[];
  ownedEvents?: Event[];
}

export interface UserCreate {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
  role?: UserRole;
}

export interface UserUpdate {
  email?: string;
  firstName?: string;
  lastName?: string;
  password?: string;
  isActive?: boolean;
  role?: UserRole;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserLoginResponse {
  token: string;
  user: User;
} 