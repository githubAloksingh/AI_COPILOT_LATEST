#!/bin/bash
if [ -f "../.env" ]; then
	set -a
	. "../.env"
	set +a
fi
mvn spring-boot:run
