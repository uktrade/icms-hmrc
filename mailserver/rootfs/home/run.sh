#!/bin/bash

: "${EMAIL_DOMAIN?Need to set EMAIL_DOMAIN}"
: "${CERTBOT_EMAIL?Need to set CERTBOT_EMAIL}"
: "${MAIL_USERNAME?Need to set MAIL_USERNAME}"
: "${MAIL_PASSWORD?Need to set MAIL_PASSWORD}"

envsubst < "/etc/postfix/main.cf.tmpl" > "/etc/postfix/main.cf"
envsubst < "/etc/dovecot/conf.d/10-auth.conf.tmpl" > "/etc/dovecot/conf.d/10-auth.conf"

if [ "$USE_LETSENCRYPT" == "yes" ]; then
  if [ ! -f "/etc/letsencrypt/live/${EMAIL_DOMAIN}/fullchain.pem"]; then
    certbot certonly --noninteractive --agree-tos --email ${CERTBOT_EMAIL} --standalone -d mail.${EMAIL_DOMAIN} -d pop3.${EMAIL_DOMAIN}
  else
    certbot renew
  fi
  postconf -e "smtpd_tls_cert_file = /etc/letsencrypt/live/mail.${EMAIL_DOMAIN}/fullchain.pem"
  postconf -e "smtpd_tls_key_file = /etc/letsencrypt/live/mail.${EMAIL_DOMAIN}/privkey.pem"
  sed -i "s/^ssl_cert = .*$/ssl_cert = \<\/etc\/letsencrypt\/live\/mail.${EMAIL_DOMAIN}\/fullchain.pem/g" /etc/dovecot/conf.d/10-ssl.conf
  sed -i "s/^ssl_key = .*$/ssl_key = \<\/etc\/letsencrypt\/live\/mail.${EMAIL_DOMAIN}\/privkey.pem/g" /etc/dovecot/conf.d/10-ssl.conf
fi

# set up emails/passwords etc.
PASSWORD_HASH=$(doveadm pw -s SHA512-CRYPT -p ${MAIL_PASSWORD})
echo "${MAIL_USERNAME}:${PASSWORD_HASH}::::::" >> /etc/dovecot/passwd
echo "${MAIL_USERNAME}@${EMAIL_DOMAIN} ${MAIL_USERNAME}" >> /etc/postfix/vmailbox
echo "postmaster@${EMAIL_DOMAIN} postmaster" >> /etc/postfix/virtual
echo "${MAIL_USERNAME}@${EMAIL_DOMAIN} ${MAIL_USERNAME}" >> /etc/postfix/virtual
postmap /etc/postfix/vmailbox
postmap /etc/postfix/virtual

rm /var/spool/postfix/pid/master.pid

cd /etc/supervisor && /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
