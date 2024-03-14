# Set up

## Add an application

Go to `/admin/linked_services/app/add/` and add the first application, it will generate automatically the keys, go to its pair and add the second application using the same key, key type and basic auth fields.

## Which algorithm you should use

The correct algorithm depends on your requirements, just avoid to use any signature algorithm, because it's significantly slower.

## Add first_party_webhooks to your scheduler

`python manage.py first_party_webhooks` routes all the incoming webhooks what was saved previously.
