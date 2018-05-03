"""Use Symfony and Doctrine to print a list of test users."""

# Initialize PHP
from phpbridge import php
php.require('vendor/autoload.php')

# Make this namespace accessible for later
import phpbridge.php.MyNamespace.Entities

# Start Symfony and get a container object
kernel = php.AppKernel('dev', False)
kernel.boot()
container = kernel.getContainer()

# Start and get an entity manager
em = container.get('doctrine.orm.entity_manager')

# You can use the class object instead of a string
users = em.getRepository(php.MyNamespace.Entities.User)

for user in users.findBy({'email': 'test@example.org'}):
    print(user.getUsername())
