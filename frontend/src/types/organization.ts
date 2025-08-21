import { User } from './user';
import { Event } from './event';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo?: string;
  website?: string;
  ownerId: string;
  createdAt: string;
  updatedAt: string;
  owner?: User;
  members?: User[];
  events?: Event[];
}

export interface OrganizationCreate {
  name: string;
  description?: string;
  logo?: string;
  website?: string;
}

export interface OrganizationUpdate {
  name?: string;
  description?: string;
  logo?: string;
  website?: string;
}

export interface OrganizationMember {
  userId: string;
  organizationId: string;
  role: string;
  user?: User;
}

export interface OrganizationMemberCreate {
  userId: string;
  role: string;
}

export interface OrganizationMemberUpdate {
  role: string;
} 