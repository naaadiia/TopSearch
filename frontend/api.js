const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const getData = async () => {
  const response = await fetch(`${API_URL}/api/data`);
  return response.json();
};