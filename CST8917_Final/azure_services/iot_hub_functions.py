import logging
from azure.iot.hub import IoTHubRegistryManager
from config.azure_config import get_azure_config

def get_iot_hub_registry_manager():
    """
    Initializes and returns an IoTHubRegistryManager instance using the connection string from the config.
    """
    config = get_azure_config()
    connection_string = config["IOTHUB_CONNECTION_STRING"]
    return IoTHubRegistryManager(connection_string)

def register_device_in_iot_hub(device_data: dict):
    """
    Registers a device in IoT Hub.
    """
    try:
        registry_manager = get_iot_hub_registry_manager()
        device_id = device_data.get("deviceId")
        if not device_id:
            raise ValueError("Device ID is required for IoT Hub registration.")
        
        # Create a device in IoT Hub
        device = registry_manager.create_device_with_sas(
            device_id=device_id,
            primary_key=None,
            secondary_key=None,
            status="enabled"
        )
        logging.info(f"Device {device_id} registered in IoT Hub successfully.")
        return device
    except Exception as e:
        logging.exception(f"Failed to register device in IoT Hub: {str(e)}")
        raise e

def delete_device_from_iot_hub(device_id: str):
    """
    Deletes a device from IoT Hub.
    """
    try:
        registry_manager = get_iot_hub_registry_manager()
        if not device_id:
            raise ValueError("Device ID is required for IoT Hub deletion.")
        
        # Delete the device from IoT Hub
        registry_manager.delete_device(device_id)
        logging.info(f"Device {device_id} deleted from IoT Hub successfully.")
    except Exception as e:
        logging.exception(f"Failed to delete device from IoT Hub: {str(e)}")
        raise e