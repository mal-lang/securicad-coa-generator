import requests
import json
import base64
import time
import zipfile
import shutil
import os


class Session:
    '''
    Representation of a session
    '''

    def __init__(self, ip_address, user):
        self.base_url = "https://{}/".format(ip_address)
        self.path_version = "api/v1/system/version"
        self.path_login = "api/v1/auth/login"
        self.path_projects = "api/v1/projects"
        self.path_project_models = "api/v1/models"
        self.path_project_models_json = "api/v1/model/json"
        self.path_project_models_files = "api/v1/model/file"
        self.path_project_scenarios = "api/v1/scenario"
        self.path_project_simulations = "api/v1/simulations"
        self.path_simulation_results = "api/v1/simulation/data"
        self.path_simulation_attack_path = "api/v1/simulation/attackpath"

        self.user = user

        self.check_cert = False
        # Set to false to skip HTTPS server cert validation.
        # Not secure and for testing only!

        status_code, self.jwt_token = self._login()
        if status_code == 200:
            print("Connection established to {} by the user {}.".format(ip_address, self.user.name))
        else:
            print("Failed to initiate session.")
            return


    def _login(self):
        response = requests.post(
            self.base_url + self.path_login,
            data='{"organization":"' + self.user.organization +
                 '","username":"' + self.user.name +
                 '","password":"' + self.user.password + '"}',
            headers={'Content-Type': 'application/json'},
            verify=self.check_cert
        )
        return (response.status_code, response.json()['response']['access_token'])


    def get_projects(self):
        response = requests.post(
            self.base_url + self.path_projects,
            headers={'Content-Type': 'application/json', 'Content-Length': '0',
                     'Authorization': 'JWT ' + self.jwt_token},
            verify=self.check_cert
        )
        if response.status_code == 200:
            projects = response.json()
            return projects
        return


    def list_projects(self):
        try:
            print(json.dumps(self.get_projects(), sort_keys=True, indent=4))
        except:
            print("Failed to fetch projects.")
        return


    def delete_model_from_project(self, model_id, project_id):
        response = requests.delete(
            self.base_url + self.path_project_models,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'JWT ' + self.jwt_token},
            data='{"pid":"' + project_id + '","mids":["' + model_id + '"]}',
            verify=self.check_cert
        )
        if response.status_code == 200:
            print('Deleted model having mid = {} from the project having pid = {}.'.format(
                model_id, project_id))
        else:
            print('Failed to delete the model.')
        return


    def delete_scenario_from_project(self, scenario_id, project_id):
        response = requests.delete(
            self.base_url + self.path_project_scenarios,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'JWT ' + self.jwt_token},
            data='{"pid":"' + project_id + '","tids":["' + scenario_id + '"]}',
            verify=self.check_cert
        )
        if response.status_code == 200:
            print('Deleted scenario having id = {} from the project having pid = {}.'.format(
                scenario_id, project_id))
        else:
            print('Failed to delete the scenario.')
        return


    def delete_simulation_from_project(self, simulation_id, project_id):
        response = requests.delete(
            self.base_url + self.path_project_simulations,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'JWT ' + self.jwt_token},
            data='{"pid":"' + project_id + '","simds":["' + simulation_id + '"]}',
            verify=self.check_cert
        )
        if response.status_code == 200:
            print('Deleted simulation having id = {} from the project having pid = {}.'.format(
                simulation_id, project_id))
        else:
            print('Failed to delete the simulation. Response status code: {}'.format(response.status_code))
        return


    # def fetch_model_as_json(self, model_id, project_id):
    #     response = requests.post(
    #         self.base_url + self.path_project_models_json,
    #         headers={
    #             'Content-Type': 'application/json',
    #             'Authorization': 'JWT ' + self.jwt_token},
    #         data='{"pid":"' + project_id + '","mids":["' + model_id + '"]}',
    #         verify=self.check_cert
    #     )
    #     if response.status_code == 200:
    #         return response.json()
    #     return


    def download_model_as_scad(self, model_id, project_id, outpath=None):
        '''
        Download model having model_id = 'model_id' from the project having id
        'project_id', save the resulting .sCAD file to the directory provided
        in 'outpath'.

        If no path provided, save in the current directory.

        If downloaded successfully, return the absolute path of the model file. Else, return None.
        '''
        response = requests.post(
            self.base_url + self.path_project_models_files,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'JWT ' + self.jwt_token},
            data='{"pid":"' + project_id + '","mids":["' + model_id + '"]}',
            verify=self.check_cert
        )
        if response.status_code == 200:
            print("Successfully downloaded model .sCAD file.")
            contents = base64.b64decode(response.json()["response"]["data"].encode())
            file_name = response.json()["response"]["name"] + "_down.sCAD"
            try:
                actual_out_path = os.path.abspath(outpath + file_name)
                info = "Saved to {}.".format(actual_out_path)
            except:
                actual_out_path = os.path.abspath(file_name)
                info = "Saved to {}.".format(actual_out_path)
            with open(actual_out_path, 'wb') as f:
                f.write(contents)
            print(info)
            return actual_out_path
        else:
            print("Failed to download the model.")
        return


    def upload_model_to_project(self, model_file_path, project_id):
        '''
        Uploads a model stored in a .sCAD file under the specified path to the project of the specified project id.

        If successful, return the model id (string). Else, return None.
        '''
        with open(model_file_path, 'rb') as f:
            file = base64.b64encode(f.read()).decode()
        if '\\' in model_file_path:
            file_name = model_file_path[model_file_path.rindex('\\'):]
        else:
            file_name = model_file_path
        data = '{"pid":"' + project_id + \
            '","files":[[{"file":"' + file + '","filename":"' + \
            file_name + '","type":"sCAD","tags":[]}]]}'
        response = requests.put(
            self.base_url + self.path_project_models,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'JWT ' + self.jwt_token},
            data=data,
            verify=self.check_cert
        )
        if response.status_code == 200:
            mid = response.json()['response'][0]["mid"]
            print('Uploaded model {} to the project having pid = {}. The model id is {}.'.format(
                model_file_path, project_id, mid))
            return mid
        else:
            print('Failed to upload a model. Response: {}.'.format(response.status_code))
        return


    def run_simulation(self, project_id, model_id, name='', description='', time_limit=30):
        '''
        Run simulation on the specified model.

        If successful, return simulation id (string). This can be later used for querring for simulation results.
        Else, return None.
        '''
        data = '{"description":"' + description + '","mid":"' + model_id + \
            '","name":"' + name + '","pid":"' + project_id + '"}'
        # sometimes fails to run a simulation even if all the data is correct. so:
        status_code = -1
        start = time.time()
        time_passed = -1
        while status_code != 200 and time_passed < time_limit:
            time.sleep(5)
            response = requests.put(
                self.base_url + self.path_project_scenarios,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'JWT ' + self.jwt_token},
                data=data,
                verify=self.check_cert
            )
            status_code = response.status_code
            time_passed = time.time() - start
        if status_code == 200:
            simid = response.json()['response']['calculation']['simid']
            print("Simulation performed.")
            return simid
        else:
            print("Failed to run a simulation. Response status code is {}.".format(response.status_code))
            return


    def get_simulation_results(self, project_id, simulation_id, time_limit=30):
        '''
        '''
        status_code = -1
        start = time.time()
        time_passed = -1
        while status_code != 200 and time_passed < time_limit:
            time.sleep(5)
            response = requests.post(
                self.base_url + self.path_simulation_results,
                data='{"pid":"' + project_id + '", "simid": "' + simulation_id + '"}',
                headers={'Content-Type': 'application/json',
                         'Authorization': 'JWT ' + self.jwt_token},
                verify=False
            )
            status_code = response.status_code
            time_passed = time.time() - start

        if status_code == 200:
            print("Simulation results fetched successfully.")
            return response.json()
        else:
            print("Failed to fetch simulation results.")
            return


    def get_attack_path_from_simulation(self, simulation_id, attack_step="3.Compromise", time_limit=30):
        '''
        Fetches attack paths created by simulation having specified id.
        If successful, returns json object containing the paths.
        Else, returns None.
        '''
        status_code = -1
        start = time.time()
        time_passed = -1
        while status_code != 200 and time_passed < time_limit:
            time.sleep(5)
            response = requests.post(
                self.base_url + self.path_simulation_attack_path,
                data='{"simid": "' + simulation_id + '", "attackstep": "' + attack_step + '"}',
                headers={'Content-Type': 'application/json',
                         'Authorization': 'JWT ' + self.jwt_token},
                verify=False
            )
            status_code = response.status_code
            time_passed = time.time() - start

        if status_code == 200:
            print("Attack paths fetched successfully.")
            return response.json()
        else:
            print("Failed to fetch attack paths.")
            return


    def get_ttcs(self, project_id, simulation_id, attack_step, time_limit=30):
        simres = self.get_simulation_results(project_id, simulation_id, time_limit=time_limit)
        for risk in simres["response"]["results"]["risks"]:
            if risk["attackstep_id"] == attack_step:
                return [round(float(risk["ttc5"]), 3), round(float(risk["ttc50"]), 3), round(float(risk["ttc95"]), 3)]


    def download_and_unzip_model(self, project_id, model_id, outpath=None, feedback = False):
        '''
        Download model having id 'model_id' from the project having id 'project_id', save the resulting
        sCAD file to the directory specified by 'outpath'.
        Unzip the sCAD archive to new directory named 'coa<the time in seconds since the epoch as a floating point number>'.

        Out: path to the .eom file storing the model.
        '''
        model_as_scad_path = self.download_model_as_scad(model_id=model_id, project_id=project_id, outpath=outpath)
        # the above ends with "_down.sCAD"
        scad_model_dir_path = model_as_scad_path[:model_as_scad_path.rindex('\\')]
        scad_model_file_name = model_as_scad_path[model_as_scad_path.rindex('\\')+1:model_as_scad_path.rindex('_')]
        extraction_dir_name = "coa{}".format(time.time()).replace('.', '_')
        extraction_dir_full_path = "{}\\{}".format(scad_model_dir_path, extraction_dir_name)
        with zipfile.ZipFile(model_as_scad_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_dir_full_path)
        eom_path = "{}\{}.eom".format(extraction_dir_full_path, scad_model_file_name)

        if feedback:
            print("//path to the .eom file: {}".format(eom_path))

        return eom_path


    def zip_and_upload_model(self, path_to_dir_with_model_files, project_id, clean_up = True):
        '''
        Given path to the directory containing three files:
            meta.json, *.eom, *cmxCanvas,
        (like the ones resulting from unpacking a .sCAD archive using the download_and_unzip_model method)
        pack them, zip'em and upload'em.

        Constructs .zip archive containing the files in the directory one level higher than the directory containing
        the files, renames it to .sCAD, uploads and removes.
        '''
        dir_one_level_higher_than_model_files = path_to_dir_with_model_files[:path_to_dir_with_model_files.rindex('\\')]
        shutil.make_archive(base_name='{}\\tempTemp'.format(dir_one_level_higher_than_model_files), format='zip',
                            root_dir=path_to_dir_with_model_files)
        zipped_model_file_path = '{}\\tempTemp.zip'.format(dir_one_level_higher_than_model_files)
        sCAD_model_file_path = '{}\\tempTemp.sCAD'.format(dir_one_level_higher_than_model_files)
        os.rename(zipped_model_file_path, sCAD_model_file_path)
        uploaded_model_id = self.upload_model_to_project(model_file_path=sCAD_model_file_path,
                                                                 project_id=project_id)
        if uploaded_model_id is not None:
            if clean_up:
                os.remove(sCAD_model_file_path)
            return uploaded_model_id
        else:
            print('Failed to upload the zipped model.')
            return
