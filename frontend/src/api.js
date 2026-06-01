import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export const calculateLiquidRelief = (data) =>
  api.post('/api/v1/liquid-relief', data).then((r) => r.data);

export const calculateGasRelief = (data) =>
  api.post('/api/v1/gas-relief', data).then((r) => r.data);

export const calculateTwoPhase = (data) =>
  api.post('/api/v1/two-phase', data).then((r) => r.data);

export const calculateFireWetted = (data) =>
  api.post('/api/v1/fire-wetted', data).then((r) => r.data);

export const calculateFireUnwetted = (data) =>
  api.post('/api/v1/fire-unwetted', data).then((r) => r.data);

export const calculateThermalExpansion = (data) =>
  api.post('/api/v1/thermal-expansion', data).then((r) => r.data);

export const getOrifices = () =>
  api.get('/api/v1/orifices').then((r) => r.data);

export const getValves = (letter) =>
  api.get(`/api/v1/valves/${letter}`).then((r) => r.data);

export const convertUnits = (data) =>
  api.post('/api/v1/convert', data).then((r) => r.data);

export const getEnvFactors = () =>
  api.get('/api/v1/env-factors').then((r) => r.data);

export const getHealth = () =>
  api.get('/health').then((r) => r.data);

export default api;
