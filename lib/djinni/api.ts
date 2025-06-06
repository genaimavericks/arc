import { getApiBaseUrl } from '../config';
import { DjinniModelType } from './store';

/**
 * Fetches the currently active Djinni model from the server
 */
export async function fetchActiveDjinniModel(): Promise<DjinniModelType> {
  try {
    const apiUrl = getApiBaseUrl();
    const token = localStorage.getItem("token");
    
    // Use the same endpoint as the admin settings API
    const response = await fetch(`${apiUrl}/api/admin/settings`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      console.error("Failed to fetch active Djinni model:", response.status);
      // Default to factory_astro if we can't fetch the setting
      return "factory_astro";
    }

    const data = await response.json();
    // Extract the djinni_active_model from the settings response
    return data.djinni_active_model || "factory_astro";
  } catch (error) {
    console.error("Error fetching active Djinni model:", error);
    // Default to factory_astro on error
    return "factory_astro";
  }
}

/**
 * Updates the active Djinni model on the server
 */
export async function updateActiveDjinniModel(model: DjinniModelType): Promise<DjinniModelType> {
  try {
    const apiUrl = getApiBaseUrl();
    const token = localStorage.getItem("token");
    
    // Use the same endpoint and format as the admin settings API
    const response = await fetch(`${apiUrl}/api/admin/settings`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ djinni_active_model: model }),
    });

    if (!response.ok) {
      console.error("Failed to update active Djinni model:", response.status);
      throw new Error("Failed to update active Djinni model");
    }

    const data = await response.json();
    return data.djinni_active_model;
  } catch (error) {
    console.error("Error updating active Djinni model:", error);
    throw error;
  }
}
