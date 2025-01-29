import docker
import io
import tarfile
import json
from pydantic import BaseModel

# Output classes
class CodeGen(BaseModel):
    code: str = "The python code only without any preamble or postamble"

class ExistingDockerRunner:
    def __init__(self, container_name_or_id):
        self.client = docker.from_env()
        self.container = self.client.containers.get(container_name_or_id)
        print(f"Connected to container: {self.container.name} (ID: {self.container.id[:12]})")

    def run_python_code(self, code):
        # Write code to a file and copy it to the container
        with io.BytesIO(code.encode('utf-8')) as file_like_object:
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='script.py')
                info.size = len(file_like_object.getvalue())
                tar.addfile(info, file_like_object)
            
            tar_buffer.seek(0)
            self.container.put_archive('/', tar_buffer)

        # Execute the Python script
        exit_code, output = self.container.exec_run("python /script.py")
        return output.decode('utf-8')

# Specific container for development
container_name_or_id = "code-runner-dev"
runner = ExistingDockerRunner(container_name_or_id)


# Tool functions
def generate_code(code: str) -> str:
    """Use this tool to generate python code and the reasoning behind the code based on the user's input."""

    result = runner.run_python_code(code)

    json_data = {
        "code": code,
        "result": result
    }

    json_string = json.dumps(json_data)

    return json_string