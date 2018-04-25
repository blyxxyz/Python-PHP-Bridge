<?php

/**
 * A stand-alone file to start a bridge without messing with composer.
 */

declare(strict_types = 1);

require_once __DIR__ . '/php/CommandServer.php';
require_once __DIR__ . '/php/StdioCommandServer.php';
require_once __DIR__ . '/php/NonFunctionProxy.php';
require_once __DIR__ . '/php/Commands.php';
require_once __DIR__ . '/php/ObjectStore.php';

(new \blyxxyz\PythonServer\StdioCommandServer)->communicate();
