This terraform file should allow you to create a completely free copy
of the minesweeper.org website using the GCP Free Tier.

But this is a some assembly required recipe.

First, install terraform.
terraform init
terraform plan
terraform apply
Make note of the output IP.

i.e. go into your domain registrar and update the A record for your hostname
to set it to the IP in the output
assume the IP output is 1.2.3.4 and the hostname is pgl.minsweeper.org
set pgl.minesweeper.org A record to 1.2.3.4

then ssh to the host
gcloud compute ssh pgl.minesweeper.org --zone=us-central1-a

What You Should Do After Logging In
While Terraform can do everything, certain tasks—like SSL certificates—are often easier to handle manually or via a configuration management tool (like Ansible) because they require the DNS to be live.

DNS Configuration: Before running Let's Encrypt, you must point pgl.minesweeper.org to the new static IP created by Terraform.

Clone the Repo: git clone your Python/JS project into /var/www/.

Python Virtual Environment: Create a venv, install FastAPI and Uvicorn.

Let's Encrypt (Certbot): Run sudo certbot --apache. This will automatically modify your Apache config to handle SSL and redirects.

Reverse Proxy Setup: You will need to configure Apache to act as a reverse proxy, sitting in front of Uvicorn.

Flow: User → Apache (Port 443) → Uvicorn/FastAPI (Port 8000).

Systemd Service: Create a service file so that Uvicorn starts automatically if the server reboots.


Post-Login Steps for Database Integration
Regardless of which method you choose, you will need to handle a few things once you SSH into the box:

Environment Variables: Do not hardcode your DB credentials in your FastAPI code. Create a .env file on the server and use python-dotenv to load the DB_USER, DB_PASS, and DB_NAME.

Drivers: Install the Python MySQL client in your virtual environment:

pip install mysql-connector-python or pip install sqlalchemy if you are using an ORM.


Remote State (Best Practice)
Right now, your "state" (the map of what you built) lives only on your local computer. If you lose that file, Terraform loses track of your server.

As a next step, you might want to store your state in a Google Cloud Storage (GCS) bucket. This makes your infrastructure more resilient and allows you to manage it from other machines later.

Would you like the code snippet to migrate your local state to a GCS bucket to make this setup "production-ready"?
