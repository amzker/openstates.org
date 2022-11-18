#!/bin/sh
set -e

# backup everything to private archive
echo "Extracting full backup..."
pg_dump -Fc openstatesorg > openstatesorg.pgdump
echo "Shipping full backup to s3"
aws s3 cp openstatesorg.pgdump "s3://openstates-backups/full-backup/$(date +%Y-%m-%d)-openstatesorg.pgdump"
rm -f openstatesorg.pgdump


# layered approach for public
echo "Executing public schema-only backup..."
pg_dump -Fc openstatesorg --schema-only > schema.pgdump
aws s3 cp --acl public-read schema.pgdump "s3://data.openstates.org/postgres/schema/$(date +%Y-%m)-schema.pgdump"

echo "Executing public data backup..."
pg_dump -Fc openstatesorg --data-only \
  --table=opencivicdata* \
  --table=django_migrations \
  --table=django_content_type \
  --table=django_site \
  > public.pgdump

echo "Uploading public backups to s3..."
aws s3 cp --acl public-read public.pgdump "s3://data.openstates.org/postgres/daily/$(date +%Y-%m-%d)-public.pgdump"
aws s3 cp --acl public-read public.pgdump "s3://data.openstates.org/postgres/monthly/$(date +%Y-%m)-public.pgdump"
