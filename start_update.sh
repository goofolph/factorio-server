#!/bin/bash

python=which python3

if [ ! -d "venv" ]; then
    $python -m venv venv
fi

source "venv/bin/activate"

pip install -U -r requirements.txt
