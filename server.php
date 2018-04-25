<?php

/**
 * A stand-alone file to start a bridge without messing with composer.
 */

declare(strict_types = 1);

require_once __DIR__ . '/php/CommandBridge.php';
require_once __DIR__ . '/php/StdioCommandBridge.php';
require_once __DIR__ . '/php/NonFunctionProxy.php';
require_once __DIR__ . '/php/Commands.php';
require_once __DIR__ . '/php/ObjectStore.php';

(new \PythonBridge\StdioCommandBridge)->communicate();
