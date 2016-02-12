#!/bin/bash

if [ -e ./build ]; then
  rm -rf ./build
fi

/bin/mkdir -p build
cp -r ./src/* build/
cp -r ./libs/* build/

cd build
python -m zipfile -c ../main.zip ./*

