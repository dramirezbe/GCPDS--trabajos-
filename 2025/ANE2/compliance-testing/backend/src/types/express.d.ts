import { Request } from 'express';

declare global {
  namespace Express {
    interface User {
      id: number;
      username: string;
      role: string;
      full_name: string;
      email: string;
    }
  }
}
