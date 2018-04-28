<?php

/**
 * A stand-alone file to start a bridge without messing with composer.
 */

declare(strict_types = 1);


// Adapted from the PHP-FIG example autoloader
spl_autoload_register(function ($class) {
    $prefix = 'blyxxyz\\PythonServer\\';
    $base_dir = __DIR__ . '/php/';

    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }

    $relative_class = substr($class, $len);

    $file = $base_dir . str_replace('\\', '/', $relative_class) . '.php';

    if (file_exists($file)) {
        /** @noinspection PhpIncludeInspection */
        require $file;
    }
});

(new \blyxxyz\PythonServer\StdioCommandServer)->communicate();
