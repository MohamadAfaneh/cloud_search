#!/usr/bin/env python3
import os
import logging
from OpenSSL import crypto

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_self_signed_cert(certs_dir):
    """
    Creates a self-signed server certificate and a CA certificate.
    Saves server.crt, server.key, ca.crt, and ca.key in the specified directory.
    """
    logger.info(f"Creating certificates in directory: {certs_dir}")
    os.makedirs(certs_dir, exist_ok=True)

    # === Server Key & Certificate ===
    server_key = crypto.PKey()
    server_key.generate_key(crypto.TYPE_RSA, 2048)

    server_cert = crypto.X509()
    subject = server_cert.get_subject()
    subject.C = "US"
    subject.ST = "State"
    subject.L = "City"
    subject.O = "Organization"
    subject.OU = "Organizational Unit"
    subject.CN = "localhost"  # This should match your domain

    server_cert.set_serial_number(1000)
    server_cert.gmtime_adj_notBefore(0)
    server_cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year
    server_cert.set_issuer(subject)
    server_cert.set_pubkey(server_key)
    server_cert.sign(server_key, 'sha256')

    server_cert_path = os.path.join(certs_dir, "server.crt")
    server_key_path = os.path.join(certs_dir, "server.key")

    with open(server_cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, server_cert))
    logger.info(f"Generated server.crt at {server_cert_path}")

    with open(server_key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, server_key))
    logger.info(f"Generated server.key at {server_key_path}")

    # Set proper permissions
    os.chmod(server_cert_path, 0o644)
    os.chmod(server_key_path, 0o600)

    # === CA Key & Certificate ===
    ca_key = crypto.PKey()
    ca_key.generate_key(crypto.TYPE_RSA, 2048)

    ca_cert = crypto.X509()
    ca_subject = ca_cert.get_subject()
    ca_subject.C = "US"
    ca_subject.ST = "State"
    ca_subject.L = "City"
    ca_subject.O = "Organization"
    ca_subject.OU = "Organizational Unit"
    ca_subject.CN = "CA"

    ca_cert.set_serial_number(1001)
    ca_cert.gmtime_adj_notBefore(0)
    ca_cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year
    ca_cert.set_issuer(ca_subject)
    ca_cert.set_pubkey(ca_key)
    ca_cert.sign(ca_key, 'sha256')

    with open(os.path.join(certs_dir, "ca.crt"), "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, ca_cert))
    logger.info("Generated ca.crt")

    with open(os.path.join(certs_dir, "ca.key"), "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key))
    logger.info("Generated ca.key")

def main():
    """Main execution function."""
    certs_dir = "/app/certs"
    logger.info(f"Starting certificate generation in {certs_dir}")

    try:
        create_self_signed_cert(certs_dir)
        logger.info("✅ Certificates generated successfully")
        # List the generated files
        for file in os.listdir(certs_dir):
            logger.info(f"Generated file: {file}")
    except Exception as e:
        logger.error(f"❌ Error generating certificates: {e}")
        raise

if __name__ == "__main__":
    main()