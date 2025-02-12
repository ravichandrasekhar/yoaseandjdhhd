import os
import json
from fastapi import HTTPException

class AppConfigManager:
    config_dir = "AppConfigs"
    
  
    def getAllProjects():
        """
        Retrieve details of all projects stored in the configuration directory.
        """
        if not os.path.exists(AppConfigManager.config_dir):
            raise HTTPException(status_code=404, detail="Configuration directory does not exist.")

        config_files = [
            f for f in os.listdir(AppConfigManager.config_dir) if f.endswith(".json")
        ]
        if not config_files:
            raise HTTPException(status_code=404, detail="No project configurations found.")

        all_projects = []

        for file in config_files:
            file_path = os.path.join(AppConfigManager.config_dir, file)
            try:
                with open(file_path, "r") as f:
                    project_data = json.load(f)

                    project_entry = {
                        "id": project_data.get("id", os.path.splitext(file)[0]),
                        "name": project_data.get("name", os.path.splitext(file)[0]),
                        "data": project_data.get("data", []),
                    }
                    all_projects.append(project_entry)
            except Exception as e:
                all_projects.append({
                    "id": os.path.splitext(file)[0],
                    "name": os.path.splitext(file)[0],
                    "data": [],
                    "error": str(e),
                })

        return all_projects


   
    def setAppConfiguration(project_name: str, data: dict):
        """
        Set or update application configuration for a project.
        """
        # Ensure the configuration directory exists
        os.makedirs(AppConfigManager.config_dir, exist_ok=True)

        # Define the file path for the project configuration
        file_path = os.path.join(AppConfigManager.config_dir, f"{project_name}.json")

        # Check if a configuration file already exists
        if os.path.exists(file_path):
            raise HTTPException(
                status_code=400,
                detail=f"Configuration for '{project_name}' already exists. Use an update function if you want to modify it."
            )

        # Save the configuration data into a JSON file
        try:
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save configuration: {str(e)}"
            )

        return {"message": f"Configuration for '{project_name}' has been saved successfully."}

   
    def editAppConfiguration(project_name: str, data: dict):
        """
        Edit an existing application configuration for a project.
        """
        # Ensure the configuration directory exists
        if not os.path.exists(AppConfigManager.config_dir):
            raise HTTPException(status_code=404, detail="Configuration directory does not exist.")

        # Define the file path for the project configuration
        file_path = os.path.join(AppConfigManager.config_dir, f"{project_name}.json")

        # Check if the project configuration file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Configuration for '{project_name}' does not exist.")

        # Save the new configuration data into the existing JSON file
        try:
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update configuration: {str(e)}"
            )

        return {"message": f"Configuration for '{project_name}' has been updated successfully."}

  
    def deleteAppConfiguration(project_name: str):
        """
        Delete a project configuration.
        """
        # Ensure the configuration directory exists
        if not os.path.exists(AppConfigManager.config_dir):
            raise HTTPException(status_code=404, detail="Configuration directory does not exist.")

        # Define the file path for the project configuration
        file_path = os.path.join(AppConfigManager.config_dir, f"{project_name}.json")

        # Check if the project configuration file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Configuration for '{project_name}' does not exist.")

        # Delete the configuration file
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete configuration: {str(e)}"
            )

        return {"message": f"Configuration for '{project_name}' has been deleted successfully."}
    
    # def deleteAppConfiguration(project_name: str, isDelete: bool):

    #     if not os.path.exists(AppConfigManager.config_dir):
    #         raise HTTPException(status_code=404, detail="Configuration directory does not exist.")

    #     file_path = os.path.join(AppConfigManager.config_dir, f"{project_name}.json")

    #     if not os.path.exists(file_path):
    #         raise HTTPException(status_code=404, detail=f"Configuration for '{project_name}' does not exist.")

    #     try:
    #         with open(file_path, "r") as file:
    #             config_data = json.load(file)

    #         config_data['isDelete'] = isDelete

    #         with open(file_path, "w") as file:
    #             json.dump(config_data, file, indent=4)
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=500,
    #             detail=f"Failed to update configuration: {str(e)}"
    #         )

    #     return {"message": f"Configuration for '{project_name}' has been updated successfully."}


    def getSingleProject(project_name: str):
        """
        get single  project configuration.
        """
        # Ensure the configuration directory exists
        if not os.path.exists(AppConfigManager.config_dir):
            raise HTTPException(status_code=404, detail="Configuration directory does not exist.")

        # Define the file path for the project configuration
        file_path = os.path.join(AppConfigManager.config_dir, f"{project_name}.json")

        # Check if the project configuration file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Configuration for '{project_name}' does not exist.")

        single_project = {}
        # Read and aggregate each JSON configuration file
        try:
            with open(file_path, "r") as f:
                single_project = json.load(f)
        except Exception as e:
            single_project = {"error": str(e)}

        return single_project