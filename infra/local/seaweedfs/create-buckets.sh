#!/bin/sh
# 로컬 S3 호환 컨테이너(SeaweedFS)에 앱 버킷을 만든다. compose 의 s3-init 서비스가 s3 가 healthy 해진 뒤 한 번 돈다.
# 버킷 이름은 backend/.env.example(STORAGE_BUCKET)·backend/.env.test 와 같아야 한다.
# 이미 있는 버킷은 건너뛴다(다시 띄워도 실패하지 않는다). 그 밖의 실패는 그대로 종료 코드로 올린다.
set -eu

MASTER="${WEED_MASTER:?WEED_MASTER 가 필요하다(예: s3:9333)}"
BUCKETS="${BUCKETS:?BUCKETS 가 필요하다(공백 구분)}"

existing="$(echo "s3.bucket.list" | weed shell -master="$MASTER")"
for bucket in $BUCKETS; do
  if echo "$existing" | grep -qE "^[[:space:]]*${bucket}[[:space:]]"; then
    echo "bucket exists: $bucket"
  else
    echo "s3.bucket.create -name $bucket" | weed shell -master="$MASTER"
    echo "bucket created: $bucket"
  fi
done
