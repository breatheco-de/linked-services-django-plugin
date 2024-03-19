# linked-services

[![PyPI - Version](https://img.shields.io/pypi/v/linked-services.svg)](https://pypi.org/project/linked-services)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/linked-services.svg)](https://pypi.org/project/linked-services)

---

**Table of Contents**

- [What does this](#what-does-this)
- [Installation](#installation)
- [License](#license)

## What does this

Linked Services was made by [4geeks.com](https://4geeks.com) to manage communication between multiple services and microservices, it manages specifically communications between pairwise services, so, if only two services share the same key, a request just could has two emisors, the other service and itself. It was designed to replace the signature algorithms because them are significally slower.

## Installation

You should install linked-services with a few optional dependencies running:

```bash
pip install linked-services[django,requests,aiohttp]
```

### Optional dependencies

#### django

- django
- djangorestframework
- celery-task-manager[django]
- adrf

#### requests

- requests
- brotli

#### httpx

- httpx
- httpcore
- h11
- idna
- brotli

#### aiohttp

- aiohttp
- aiodns
- brotli

## License

`linked-services` is distributed under the terms of the [LGPL 3.0](https://spdx.org/licenses/LGPL-3.0-or-later.html) license.
