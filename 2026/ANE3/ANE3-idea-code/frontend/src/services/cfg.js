const IS_DEV = import.meta.env.DEV;

const API_URL = IS_DEV 
  ? `${import.meta.env.VITE_API_DEV_URL}:${import.meta.env.VITE_API_DEV_PORT}${import.meta.env.VITE_API_DEV_ENDPOINT}`
  : `${import.meta.env.VITE_API_URL}:${import.meta.env.VITE_API_PORT}${import.meta.env.VITE_API_ENDPOINT}`;

export const cfg = {
  API_URL,
  IS_DEV
};