import os
import json
import logging
import azure.functions as func

# Import all modules
from CST8917_Final.functions import device_functions
from functions import image_functions
from functions import telemetry_functions
from functions import trigger_functions
from functions import user_functions
from config.azure_config import get_azure_config

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="Ping")
@app.route(route="ping", methods=["GET"])
def Ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Function App is running", status_code=200)


@app.function_name(name="SwaggerYaml")
@app.route(route="swagger", methods=["GET"])
def SwaggerYaml(req: func.HttpRequest) -> func.HttpResponse:
    try:
        yaml_path = os.path.join(os.getcwd(), 'swagger', 'swagger.yaml')
        with open(yaml_path, 'r') as file:
            return func.HttpResponse(file.read(), mimetype='application/x-yaml', status_code=200)
    except Exception as ex:
        return func.HttpResponse(f"Error loading YAML: {str(ex)}", status_code=500)

@app.function_name(name="SwaggerUI")
@app.route(route="swagger-ui", methods=["GET"])
def SwaggerUI(req: func.HttpRequest) -> func.HttpResponse:
    try:
        html_path = os.path.join(os.getcwd(), 'static', 'index.html')
        with open(html_path, 'r') as file:
            return func.HttpResponse(file.read(), mimetype='text/html', status_code=200)
    except Exception as ex:
        return func.HttpResponse(f"Error loading Swagger UI: {str(ex)}", status_code=500)

@app.function_name(name="UserFunctions")
@app.route(route="user", methods=["POST", "GET", "PUT", "PATCH", "DELETE"])
def UserManagement(req: func.HttpRequest) -> func.HttpResponse:
    # Dispatch the request to the main function in user_management.py
    return user_functions.main(req)
