<?php

/**
 * A stand-alone file to start a bridge without messing with composer.
 *
 * $argv[1] and $argv[2] should contain the files to be opened by
 * StdioCommandserver. A typical invocation might be
 * php path/to/server.php php://stdin php://stderr.
 */

declare(strict_types=1);


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

$server = new \blyxxyz\PythonServer\StdioCommandServer($argv[1], $argv[2]);
$server::promoteWarnings();
try {
    $server->communicate();
} catch (\blyxxyz\PythonServer\Exceptions\ConnectionLostException $exception) {
}
