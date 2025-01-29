import docker
import io
import tarfile
import json
from pydantic import BaseModel

# Output classes
class CodeGen(BaseModel):
    python_code: str = "The generated python code only without any preamble or postamble"

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
async def run_python_code(python_code: str) -> str:
    """Use this tool to run python code."""

    result = runner.run_python_code(python_code)

    json_data = {
        "python_code": python_code,
        "result": result
    }

    json_string = json.dumps(json_data)

    return json_string