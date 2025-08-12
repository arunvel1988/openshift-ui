import os
import shutil
import subprocess
from flask import Flask, render_template

app = Flask(__name__)

def get_os_family():
    if os.path.exists("/etc/debian_version"):
        return "debian"
    elif os.path.exists("/etc/redhat-release"):
        return "redhat"
    else:
        return "unknown"

def install_package(tool, os_family):
    package_map = {
        "docker": "docker.io" if os_family == "debian" else "docker",
        "pip3": "python3-pip",
        "python3-venv": "python3-venv"
    }
    package_name = package_map.get(tool, tool)

    try:
        if os_family == "debian":
            subprocess.run(["sudo", "apt", "update"], check=True)
            if tool == "terraform":
                subprocess.run(["sudo", "apt", "install", "-y", "wget", "gnupg", "software-properties-common", "curl"], check=True)
                
                subprocess.run([
                    "wget", "-O", "hashicorp.gpg", "https://apt.releases.hashicorp.com/gpg"
                ], check=True)
                subprocess.run([
                    "gpg", "--dearmor", "--output", "hashicorp-archive-keyring.gpg", "hashicorp.gpg"
                ], check=True)
                subprocess.run([
                    "sudo", "mv", "hashicorp-archive-keyring.gpg", "/usr/share/keyrings/hashicorp-archive-keyring.gpg"
                ], check=True)

                codename = subprocess.check_output(["lsb_release", "-cs"], text=True).strip()
                apt_line = (
                    f"deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] "
                    f"https://apt.releases.hashicorp.com {codename} main\n"
                )
                with open("hashicorp.list", "w") as f:
                    f.write(apt_line)
                subprocess.run(["sudo", "mv", "hashicorp.list", "/etc/apt/sources.list.d/hashicorp.list"], check=True)

                subprocess.run(["sudo", "apt", "update"], check=True)
                subprocess.run(["sudo", "apt", "install", "-y", "terraform"], check=True)
            else:
                subprocess.run(["sudo", "apt", "install", "-y", package_name], check=True)

        elif os_family == "redhat":
            if tool == "terraform":
                subprocess.run(["sudo", "yum", "install", "-y", "yum-utils"], check=True)
                subprocess.run([
                    "sudo", "yum-config-manager", "--add-repo",
                    "https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo"
                ], check=True)
                subprocess.run(["sudo", "yum", "install", "-y", "terraform"], check=True)
            else:
                subprocess.run(["sudo", "yum", "install", "-y", package_name], check=True)
        else:
            return False, "Unsupported OS"
        return True, None
    except Exception as e:
        return False, str(e)

@app.route("/pre-req")
def prereq():
    tools = ["pip3", "podman", "openssl", "docker", "terraform"]
    results = {}
    os_family = get_os_family()

    for tool in tools:
        if shutil.which(tool):
            results[tool] = "✅ Installed"
        else:
            success, error = install_package(tool, os_family)
            if success:
                results[tool] = "❌ Not Found → 🛠️ Installed"
            else:
                results[tool] = f"❌ Not Found → ❌ Error: {error}"



    docker_installed = shutil.which("docker") is not None
    return render_template("prereq.html", results=results, os_family=os_family, docker_installed=docker_installed)












# Check if Portainer is actually installed and running (or exists as a container)
def is_portainer_installed():
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "portainer"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
        )
        return result.stdout.strip() in ["true", "false"]
    except Exception:
        return False

# Actually run Portainer
def run_portainer():
    try:
        subprocess.run(["docker", "volume", "create", "portainer_data"], check=True)
        subprocess.run([
            "docker", "run", "-d",
            "-p", "9443:9443", "-p", "9000:9000",
            "--name", "portainer",
            "--restart=always",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "-v", "portainer_data:/data",
            "portainer/portainer-ce:latest"
        ], check=True)
        return True, "✅ Portainer installed successfully."
    except subprocess.CalledProcessError as e:
        return False, f"❌ Docker Error: {str(e)}"

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/install_portainer", methods=["GET", "POST"])
def install_portainer_route():
    installed = is_portainer_installed()
    portainer_url = "https://localhost:9443"
    message = None

    if request.method == "POST":
        if not installed:
            success, message = run_portainer()
            installed = success
        else:
            message = "ℹ️ Portainer is already installed."

    return render_template("portainer.html", installed=installed, message=message, url=portainer_url)




##################ANSIBLE INSTALLATION##################

@app.route("/openshift")
def ansible_info():
    return render_template("openshift_info.html")





from flask import render_template, request
import os
import subprocess
import shutil
import platform
import psutil

@app.route("/openshift/install")
def openshift_install():
    output_logs = ""
    repo_dir = "/tmp/crc_setup"
    pull_secret_filename = "pull-secret.txt"
    pull_secret_path = os.path.abspath(pull_secret_filename)

    try:
        # --------------------------------------------------------
        # 🧠 PRE-REQUISITES CHECK
        # --------------------------------------------------------
        output_logs += "🔍 Checking system pre-requisites...\n"

        # Check OS support
        dist_name = platform.linux_distribution()[0] if hasattr(platform, 'linux_distribution') else platform.freedesktop_os_release().get('ID', '')
        os_supported = any(os_name in dist_name.lower() for os_name in ['rhel', 'centos', 'fedora'])
        if not os_supported:
            output_logs += f"⚠️ WARNING: Your OS ({dist_name}) is not officially supported. CRC supports RHEL, CentOS, Fedora.\n"

        # Check CPU cores
        cpu_count = psutil.cpu_count(logical=False)
        if cpu_count < 4:
            output_logs += f"❌ Insufficient CPU cores. Required: 4, Found: {cpu_count}\n"
            return render_template("openshift_install.html", result=output_logs)

        # Check RAM
        mem_gb = psutil.virtual_memory().total / (1024 ** 3)
        if mem_gb < 10.5:
            output_logs += f"❌ Insufficient RAM. Required: 10.5 GB, Found: {mem_gb:.2f} GB\n"
            return render_template("openshift_install.html", result=output_logs)

        # Check Disk
        disk_gb = shutil.disk_usage("/").free / (1024 ** 3)
        if disk_gb < 35:
            output_logs += f"❌ Insufficient Disk Space. Required: 35 GB, Found: {disk_gb:.2f} GB\n"
            return render_template("openshift_install.html", result=output_logs)

        output_logs += f"✅ Pre-requisites met: {cpu_count} cores, {mem_gb:.2f} GB RAM, {disk_gb:.2f} GB disk\n"

        # --------------------------------------------------------
        # 🚀 CLONE CRC SETUP REPO IF NEEDED
        # --------------------------------------------------------
        if not os.path.exists(repo_dir):
            subprocess.run(["git", "clone", "https://github.com/arunvel1988/crc_setup", repo_dir], check=True)
            output_logs += f"✅ Cloned CRC setup repo to {repo_dir}\n"
        else:
            output_logs += f"✅ Repo already cloned at {repo_dir}, skipping clone\n"

        os.chdir(repo_dir)

        # --------------------------------------------------------
        # 🔍 Check if CRC is installed
        # --------------------------------------------------------
        try:
            crc_version = subprocess.check_output(["crc", "version"], text=True)
            output_logs += f"✅ CRC binary found:\n{crc_version}\n"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If not found, extract and move CRC binary
            output_logs += "📦 CRC binary not found, extracting...\n"
            subprocess.run(["tar", "-xf", "crc-linux-amd64.tar.xz"], check=True)

            for root, dirs, files in os.walk(repo_dir):
                if "crc" in files:
                    crc_path = os.path.join(root, "crc")
                    break
            else:
                raise Exception("❌ CRC binary not found after extraction.")

            subprocess.run(["sudo", "mv", crc_path, "/usr/local/bin/crc"], check=True)
            subprocess.run(["sudo", "chmod", "+x", "/usr/local/bin/crc"], check=True)
            output_logs += "✅ Installed CRC binary to /usr/local/bin\n"

        # --------------------------------------------------------
        # 🔑 Check pull-secret.txt
        # --------------------------------------------------------
        output_logs += f"🔍 Looking for pull-secret.txt at: {pull_secret_path}\n"
        if not os.path.exists(pull_secret_path):
            raise Exception("❌ Required pull-secret.txt not found in current directory.")
        output_logs += "✅ pull-secret.txt found.\n"

        # --------------------------------------------------------
        # ⚙️ Run CRC setup
        # --------------------------------------------------------
        output_logs += "⚙️ Running crc setup...\n"
        setup_output = subprocess.check_output(["crc", "setup"], text=True)
        output_logs += setup_output + "\n"

        # --------------------------------------------------------
        # 🚀 Start CRC
        # --------------------------------------------------------
        output_logs += "🚀 Starting CRC with pull-secret.txt...\n"
        try:
            start_cmd = ["crc", "start"]
            start_output = subprocess.check_output(start_cmd, text=True)
            output_logs += start_output
        except subprocess.CalledProcessError as e:
            output_logs += f"❌ crc start failed:\n{e.output}"

        # --------------------------------------------------------
        # 🎉 Final Info
        # --------------------------------------------------------
        final_crc_version = subprocess.check_output(["crc", "version"], text=True)
        output_logs += f"\n✅ Final CRC Version Info:\n{final_crc_version}"

    except Exception as e:
        output_logs += f"\n⚠️ Error occurred:\n{str(e)}"

    return render_template("openshift_install.html", result=output_logs)




@app.route("/openshift/cli")
def openshift_cli():
    # Check if 'oc' CLI exists in PATH
    oc_path = shutil.which("oc")

    # If installed, try to get version
    oc_version = None
    if oc_path:
        try:
            result = subprocess.run(
                ["oc", "version", "--client=true"],
                capture_output=True,
                text=True,
                check=True
            )
            oc_version = result.stdout.strip()
        except subprocess.CalledProcessError:
            oc_version = "Unable to get version"

    return render_template(
        "openshift_cli.html",
        oc_path=oc_path,
        oc_version=oc_version
    )


@app.route("/openshift/apps")
def openshift_apps():
    return render_template("openshift_apps.html")
    
@app.route("/openshift/storage")
def openshift_storage():
    return render_template("openshift_storage.html")

@app.route("/openshift/security")
def openshift_security():
    try:
        return render_template("openshift_security.html")
    except Exception as e:
        return f"Error loading page: {e}", 500

@app.route("/openshift/gitops")
def openshift_gitops():
    try:
        return render_template("openshift_gitops.html")
    except Exception as e:
        return f"Error loading GitOps page: {e}", 500


####################oc cli ###########################################





import os
from flask import render_template, request
import subprocess

OPENSHIFT_BASE = os.path.abspath("openshift")  # folder where YAMLs are stored

@app.route("/openshift/local/tutorials", methods=["GET"])
def openshift_tutorials():
    try:
        modules = sorted(os.listdir(OPENSHIFT_BASE))
        return render_template("oc_tutorials.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading OpenShift YAML tutorials: {str(e)}</pre>"

@app.route("/openshift/local/tutorials/<module>/", methods=["GET"])
def preview_openshift_yaml(module):
    module_path = os.path.join(OPENSHIFT_BASE, module)

    try:
        yaml_files = [f for f in os.listdir(module_path) if f.endswith(".yaml") or f.endswith(".yml")]
        if not yaml_files:
            return f"<pre>❌ No YAML files found in {module}</pre>"

        file_contents = {}
        for yf in yaml_files:
            file_contents[yf] = open(os.path.join(module_path, yf)).read()

        return render_template("oc_preview.html", module=module, yaml_files=file_contents)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"

@app.route("/openshift/local/tutorials/<module>/<command>", methods=["POST"])
def run_oc_command(module, command):
    module_path = os.path.join(OPENSHIFT_BASE, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    # Whitelisted oc commands
    valid_commands = {
        "apply": ["oc", "apply", "-f", module_path],
        "delete": ["oc", "delete", "-f", module_path],
        "get": ["oc", "get", "-f", module_path, "-o", "yaml"],
        "describe": ["oc", "describe", "-f", module_path]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)
        return render_template("oc_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)
    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500




#########################################################################################
# terraorm backend




@app.route('/terraform/local/tutorials/remote_backend/')
def remote_backend():
    return render_template('remote_backend.html')


def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) == 0



@app.route('/start_minio')
def start_minio():
    client = docker.from_env()
    volume_name = "minio_data"
    minio_port = 9990
    console_port = 9991

    # Check if ports are already used
    if is_port_open('localhost', minio_port) or is_port_open('localhost', console_port):
        return render_template("start_minio.html",
            emoji="⚠️",
            title="Ports in Use",
            message=f"Ports {minio_port} or {console_port} are already in use. Please stop the conflicting service or use different ports.",
            links=[]
        )

    # Check if MinIO container is already running
    try:
        container = client.containers.get("minio")
        if container.status == "running":
            return render_template("start_minio.html",
                emoji="✅",
                title="MinIO is already running",
                message="Access it using the links below.",
                links=[
                    {"label": "📦 MinIO Service", "url": f"http://localhost:{minio_port}"},
                    {"label": "🛠️ MinIO Console", "url": f"http://localhost:{console_port}"}
                ]
            )
    except docker.errors.NotFound:
        pass

    # Create volume if not present
    try:
        client.volumes.get(volume_name)
    except docker.errors.NotFound:
        client.volumes.create(name=volume_name)

    # Run MinIO container
    try:
        client.containers.run(
            "minio/minio",
            "server /data --console-address :9001",
            name="minio",
            ports={"9000/tcp": minio_port, "9001/tcp": console_port},
            environment={
                "MINIO_ROOT_USER": "minioadmin",
                "MINIO_ROOT_PASSWORD": "minioadmin"
            },
            volumes={volume_name: {"bind": "/data", "mode": "rw"}},
            detach=True
        )

        return render_template("start_minio.html",
            emoji="🚀",
            title="MinIO Started",
            message="MinIO was successfully launched with persistent volume.",
            links=[
                {"label": "📦 MinIO Endpoint", "url": f"http://localhost:{minio_port}"},
                {"label": "🛠️ MinIO Console", "url": f"http://localhost:{console_port}"}
            ]
        )

    except docker.errors.APIError as e:
        return render_template("start_minio.html",
            emoji="❌",
            title="Docker Error",
            message=e.explanation,
            links=[]
        )


###############################################################################################################


# terraform workspace ######################################



import re

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


TERRAFORM_DIR = "./local_workspace"
@app.route("/terraform/workspace")
def terraform_workspace():
    return render_template("workspace.html")

@app.route("/terraform/workspace/create", methods=["GET", "POST"])
def create_workspace():
    message = None

    if request.method == "POST":
        workspace_name = request.form["workspace_name"]

        result = subprocess.run(
            ["terraform", "workspace", "new", workspace_name],
            cwd=TERRAFORM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        message = strip_ansi_codes(result.stdout)

    return render_template("create_workspace.html", message=message)


@app.route("/terraform/workspace/delete", methods=["GET", "POST"])
def delete_workspace():
    message = None

    if request.method == "POST":
        workspace_name = request.form["workspace_name"]

        result = subprocess.run(
            ["terraform", "workspace", "delete", workspace_name],
            cwd=TERRAFORM_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        message = strip_ansi_codes(result.stdout)

    return render_template("delete_workspace.html", message=message)


@app.route("/terraform/workspace/list", methods=["GET"])
def list_workspaces():
    result = subprocess.run(
        ["terraform", "workspace", "list"],
        cwd=TERRAFORM_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    output_lines = result.stdout.strip().splitlines()
    return render_template("list_workspaces.html", workspaces=output_lines)


@app.route("/terraform/workspace/deploy", methods=["GET", "POST"])
def deploy_to_workspaces():
    output = ""
    workspaces = []

    # Fetch available workspaces using `terraform workspace list`
    try:
        result = subprocess.run(
            ["terraform", "workspace", "list"],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        # Clean up and parse the output
        for line in result.stdout.splitlines():
            workspace = line.strip().replace("*", "").strip()
            if workspace:
                workspaces.append(workspace)
    except subprocess.CalledProcessError as e:
        output = f"❌ Error fetching workspaces: {e.stderr}"

    # If form submitted (POST), deploy to selected workspaces
    if request.method == "POST":
        selected_envs = request.form.getlist("environments")
        for env in selected_envs:
            try:
                subprocess.run(["terraform", "workspace", "select", env], cwd=TERRAFORM_DIR, capture_output=True)
                subprocess.run(["terraform", "init"], cwd=TERRAFORM_DIR, capture_output=True)
                apply_result = subprocess.run(
                    ["terraform", "apply", "-auto-approve"],
                    cwd=TERRAFORM_DIR,
                    capture_output=True,
                    text=True
                )
                output += f"\n--- 🌍 {env.upper()} ---\n{apply_result.stdout}\n"
            except subprocess.CalledProcessError as e:
                output += f"\n❌ Error in {env}: {e.stderr}"

    return render_template("deploy_workspace.html", workspaces=workspaces, output=output)


######################################## playbooks #################################################



@app.route("/terraform/localstack")
def terraform_localstack():
    return render_template("localstack_info.html")



from flask import Response
import subprocess

@app.route("/terraform/localstack/install")
def install_localstack():
    # Step 1: Check if LocalStack container is already running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=localstack/localstack", "--format", "{{.ID}}"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>LocalStack Status</title>
                </head>
                <body style="font-family: Arial, sans-serif;">
                    <h2>✅ LocalStack is already running!</h2>
                    <p>You can access it at: 
                        <a href="http://localhost:4566" target="_blank">http://localhost:4566</a>
                    </p>
                    <p>🧰 <a href="https://docs.localstack.cloud/get-started/installation/" target="_blank">
                        Official Installation Docs</a>
                    </p>
                    <br>
                    <a href="/terraform/localstack">
                        <button style="padding: 10px 20px; background-color: #2b6cb0; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            ⬅️ Back to LocalStack Info
                        </button>
                    </a>

                    <a href="/terraform/localstack/tutorials">
                    <button style="padding: 10px 20px; background-color: #2b6cb0; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        LocalStack Tutorials
                    </button>
                </a>
                </body>
                </html>
            """
            return Response(html, mimetype="text/html")
    except Exception as e:
        return Response(f"<h2>❌ Error checking Docker containers: {e}</h2>", mimetype="text/html")

    # Step 2: Run LocalStack using docker run
    try:
        subprocess.Popen([
            "docker", "run",
            "--rm", "-d",
            "-p", "4566:4566",
            "-p", "4510-4559:4510-4559",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "localstack/localstack"
        ])
        html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>LocalStack Starting</title>
            </head>
            <body style="font-family: Arial, sans-serif;">
                <h2>🚀 LocalStack is starting up!</h2>
                <p>Wait a few seconds, then access it here: 
                    <a href="http://localhost:4566" target="_blank">http://localhost:4566</a>
                </p>
                <p>🧰 <a href="https://docs.localstack.cloud/get-started/installation/" target="_blank">
                    Official Installation Docs</a>
                </p>
                <br>
                <a href="/terraform/localstack">
                    <button style="padding: 10px 20px; background-color: #2b6cb0; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        ⬅️ Back to LocalStack Info
                    </button>
                </a>
                <a href="/terraform/localstack/tutorials">
                    <button style="padding: 10px 20px; background-color: #2b6cb0; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        LocalStack Tutorials
                    </button>
                </a>
            </body>
            </html>
        """
        return Response(html, mimetype="text/html")

    except Exception as e:
        return Response(f"<h2>❌ Error launching LocalStack: {e}</h2>", mimetype="text/html")

import os

TERRAFORM_BASE_LOCALSTACK = os.path.abspath("localstack")

@app.route("/terraform/localstack/tutorials", methods=["GET"])
def terraform_localstack_tutorials():
    try:
        modules = sorted(os.listdir(TERRAFORM_BASE_LOCALSTACK))
        return render_template("tf_tutorials_localstack.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading tutorials: {str(e)}</pre>"





@app.route("/terraform/localstack/tutorials/<module>/", methods=["GET"])
def preview_localstack_module(module):
    module_path = os.path.join(TERRAFORM_BASE_LOCALSTACK, module)

    try:
        main_tf = os.path.join(module_path, "main.tf")
        tfvars = os.path.join(module_path, "terraform.tfvars")

        if not os.path.exists(main_tf):
            return f"<pre>❌ main.tf not found in {module}</pre>"

        main_content = open(main_tf).read()
        var_content = open(tfvars).read() if os.path.exists(tfvars) else "No terraform.tfvars found."

        return render_template("tf_preview_localstack.html", module=module, main_tf=main_content, tfvars=var_content)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"


@app.route("/terraform/localstack/tutorials/<module>/<command>", methods=["POST"])
def run_terraform_localstack_command(module, command):
    module_path = os.path.join(TERRAFORM_BASE_LOCALSTACK, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    os.chdir(module_path)

    # Whitelisted terraform commands
    valid_commands = {
        "plan": ["terraform", "plan"],
        "apply": ["terraform", "apply", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-auto-approve"],
        "show": ["terraform", "show"],
        "output": ["terraform", "output"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt"]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        # Always init first
        subprocess.run(["terraform", "init", "-input=false"], check=True, capture_output=True, text=True)

        # Run the actual command
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)

        return render_template("tf_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)

    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500



########################## Terraform AWS - start ##########################################################


@app.route("/terraform/aws")
def terraform_aws():
    return render_template("aws_info.html")





import os

TERRAFORM_BASE_AWS = os.path.abspath("aws")

@app.route("/terraform/aws/tutorials", methods=["GET"])
def terraform_aws_tutorials():
    try:
        modules = sorted(os.listdir(TERRAFORM_BASE_AWS))
        return render_template("tf_tutorials_aws.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading tutorials: {str(e)}</pre>"





@app.route("/terraform/aws/tutorials/<module>/", methods=["GET"])
def preview_aws_module(module):
    module_path = os.path.join(TERRAFORM_BASE_AWS, module)

    try:
        main_tf = os.path.join(module_path, "main.tf")
        tfvars = os.path.join(module_path, "terraform.tfvars")

        if not os.path.exists(main_tf):
            return f"<pre>❌ main.tf not found in {module}</pre>"

        main_content = open(main_tf).read()
        var_content = open(tfvars).read() if os.path.exists(tfvars) else "No terraform.tfvars found."

        return render_template("tf_preview_aws.html", module=module, main_tf=main_content, tfvars=var_content)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"


@app.route("/terraform/aws/tutorials/<module>/<command>", methods=["POST"])
def run_terraform_aws_command(module, command):
    module_path = os.path.join(TERRAFORM_BASE_AWS, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    os.chdir(module_path)

    # Whitelisted terraform commands
    valid_commands = {
        "plan": ["terraform", "plan"],
        "apply": ["terraform", "apply", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-auto-approve"],
        "show": ["terraform", "show"],
        "output": ["terraform", "output"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt"]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        # Always init first
        subprocess.run(["terraform", "init", "-input=false"], check=True, capture_output=True, text=True)

        # Run the actual command
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)

        return render_template("tf_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)

    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500
    
    ################################## terraform aws =  end ##########################################


    ################################## terraform azure start ##########################################

@app.route("/terraform/azure")
def terraform_azure():
    return render_template("azure_info.html")





import os

TERRAFORM_BASE_AZURE = os.path.abspath("azure")

@app.route("/terraform/azure/tutorials", methods=["GET"])
def terraform_azure_tutorials():
    try:
        modules = sorted(os.listdir(TERRAFORM_BASE_AZURE))
        return render_template("tf_tutorials_azure.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading tutorials: {str(e)}</pre>"





@app.route("/terraform/azure/tutorials/<module>/", methods=["GET"])
def preview_azure_module(module):
    module_path = os.path.join(TERRAFORM_BASE_AZURE, module)

    try:
        main_tf = os.path.join(module_path, "main.tf")
        tfvars = os.path.join(module_path, "terraform.tfvars")

        if not os.path.exists(main_tf):
            return f"<pre>❌ main.tf not found in {module}</pre>"

        main_content = open(main_tf).read()
        var_content = open(tfvars).read() if os.path.exists(tfvars) else "No terraform.tfvars found."

        return render_template("tf_preview_azure.html", module=module, main_tf=main_content, tfvars=var_content)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"


@app.route("/terraform/azure/tutorials/<module>/<command>", methods=["POST"])
def run_terraform_azure_command(module, command):
    module_path = os.path.join(TERRAFORM_BASE_AWS, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    os.chdir(module_path)

    # Whitelisted terraform commands
    valid_commands = {
        "plan": ["terraform", "plan"],
        "apply": ["terraform", "apply", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-auto-approve"],
        "show": ["terraform", "show"],
        "output": ["terraform", "output"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt"]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        # Always init first
        subprocess.run(["terraform", "init", "-input=false"], check=True, capture_output=True, text=True)

        # Run the actual command
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)

        return render_template("tf_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)

    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500
    
     ################################## terraform azure end ##########################################



    ################################## terraform gcp start ##########################################

@app.route("/terraform/gcp")
def terraform_gcp():
    return render_template("gcp_info.html")





import os

TERRAFORM_BASE_GCP = os.path.abspath("gcp")

@app.route("/terraform/gcp/tutorials", methods=["GET"])
def terraform_gcp_tutorials():
    try:
        modules = sorted(os.listdir(TERRAFORM_BASE_GCP))
        return render_template("tf_tutorials_gcp.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading tutorials: {str(e)}</pre>"





@app.route("/terraform/gcp/tutorials/<module>/", methods=["GET"])
def preview_gcp_module(module):
    module_path = os.path.join(TERRAFORM_BASE_GCP, module)

    try:
        main_tf = os.path.join(module_path, "main.tf")
        tfvars = os.path.join(module_path, "terraform.tfvars")

        if not os.path.exists(main_tf):
            return f"<pre>❌ main.tf not found in {module}</pre>"

        main_content = open(main_tf).read()
        var_content = open(tfvars).read() if os.path.exists(tfvars) else "No terraform.tfvars found."

        return render_template("tf_preview_gcp.html", module=module, main_tf=main_content, tfvars=var_content)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"


@app.route("/terraform/gcp/tutorials/<module>/<command>", methods=["POST"])
def run_terraform_gcp_command(module, command):
    module_path = os.path.join(TERRAFORM_BASE_GCP, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    os.chdir(module_path)

    # Whitelisted terraform commands
    valid_commands = {
        "plan": ["terraform", "plan"],
        "apply": ["terraform", "apply", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-auto-approve"],
        "show": ["terraform", "show"],
        "output": ["terraform", "output"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt"]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        # Always init first
        subprocess.run(["terraform", "init", "-input=false"], check=True, capture_output=True, text=True)

        # Run the actual command
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)

        return render_template("tf_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)

    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500
    
     ################################## terraform gcp end ##########################################



################################## terraform modules start ##########################################



@app.route("/terraform/modules")
def terraform_modules():
    return render_template("terraform_modules_info.html")





TERRAFORM_BASE_MODULES = os.path.abspath("modules")

@app.route("/terraform/modules/tutorials", methods=["GET"])
def terraform_modules_tutorials():
    try:
        modules = sorted(os.listdir(TERRAFORM_BASE_MODULES))
        return render_template("tf_tutorials_modules.html", modules=modules)
    except Exception as e:
        return f"<pre>❌ Error loading tutorials: {str(e)}</pre>"





@app.route("/terraform/modules/tutorials/<module>/", methods=["GET"])
def preview_demo_module(module):
    module_path = os.path.join(TERRAFORM_BASE_MODULES, module)

    try:
        main_tf = os.path.join(module_path, "main.tf")
        tfvars = os.path.join(module_path, "terraform.tfvars")

        if not os.path.exists(main_tf):
            return f"<pre>❌ main.tf not found in {module}</pre>"

        main_content = open(main_tf).read()
        var_content = open(tfvars).read() if os.path.exists(tfvars) else "No terraform.tfvars found."

        return render_template("tf_preview_modules.html", module=module, main_tf=main_content, tfvars=var_content)

    except Exception as e:
        return f"<pre>❌ Error: {str(e)}</pre>"


@app.route("/terraform/modules/tutorials/<module>/<command>", methods=["POST"])
def run_terraform_modules_command(module, command):
    module_path = os.path.join(TERRAFORM_BASE_MODULES, module)

    if not os.path.isdir(module_path):
        return f"<pre>❌ Module not found: {module_path}</pre>", 404

    os.chdir(module_path)

    # Whitelisted terraform commands
    valid_commands = {
        "plan": ["terraform", "plan"],
        "apply": ["terraform", "apply", "-auto-approve"],
        "destroy": ["terraform", "destroy", "-auto-approve"],
        "show": ["terraform", "show"],
        "output": ["terraform", "output"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt"]
    }

    if command not in valid_commands:
        return f"<pre>❌ Unsupported command: {command}</pre>", 400

    try:
        # Always init first
        subprocess.run(["terraform", "init", "-input=false"], check=True, capture_output=True, text=True)

        # Run the actual command
        result = subprocess.run(valid_commands[command], capture_output=True, text=True)

        return render_template("tf_output.html",
                               command=f"{command}: {module}",
                               stdout=result.stdout,
                               stderr=result.stderr)

    except subprocess.CalledProcessError as e:
        return render_template("error.html", command=command, stderr=e.stderr), 500


################################## terraform modules end ##########################################




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=True)
