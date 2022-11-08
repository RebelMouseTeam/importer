# Objective

This repository was created specifically for RebelMouse clients who want to perform a content import from their current platform to RebelMouse.



# Getting started
To run this, you will need docker installed
## OSX and Linux

```bash
docker-compose up --build
```

## Windows 10

```bash
docker-compose.exe up --build
```
Scripts code can be found in: `/src/`

Default entrypoint without any parameters: `/src/script.py`

Your data dump should be placed into: `/data/`

Place your account credentials: `/docker.env`

NOTE: This environment is using Python and MongoDB.
