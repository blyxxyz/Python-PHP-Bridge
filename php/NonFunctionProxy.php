<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

/**
 * Provide function-like language constructs as static methods.
 *
 * `isset` and `empty` are not provided because it's impossible for a real
 * function to check whether its argument is defined.
 */
class NonFunctionProxy
{
    /**
     * @param mixed $arg1
     * @param mixed ...$rest
     *
     * @return void
     */
    public static function echo($arg1, ...$rest)
    {
        echo $arg1;
        foreach ($rest as $arg) {
            echo $arg;
        }
    }

    /**
     * @param mixed $arg
     *
     * @return int
     */
    public static function print($arg): int
    {
        return print $arg;
    }

    /**
     * @param string $code
     *
     * @return mixed
     */
    public static function eval(string $code)
    {
        return eval($code);
    }

    /**
     * @param mixed $status
     *
     * @return void
     */
    public static function exit($status = 0)
    {
        exit($status);
    }

    /**
     * @param mixed $status
     *
     * @return void
     */
    public static function die($status = 0)
    {
        die($status);
    }

    /**
     * @param string $file
     *
     * @return mixed
     *
     * @psalm-suppress UnresolvableInclude
     */
    public static function include(string $file)
    {
        return include $file;
    }

    /**
     * @param string $file
     *
     * @return mixed
     *
     * @psalm-suppress UnresolvableInclude
     */
    public static function require(string $file)
    {
        return require $file;
    }

    /**
     * @param string $file
     *
     * @return mixed
     *
     * @psalm-suppress UnresolvableInclude
     */
    public static function include_once(string $file)  // phpcs:ignore
    {
        return include_once $file;
    }

    /**
     * @param string $file
     *
     * @return mixed
     *
     * @psalm-suppress UnresolvableInclude
     */
    public static function require_once(string $file)  // phpcs:ignore
    {
        return require_once $file;
    }

    /*
     * Casting uses function calls in Python, so it may make sense to provide
     * hem as functions. These are valid function names, so they could be
     * silently overridden by proper functions. Use with care.
     */

    /**
     * @param mixed $val
     *
     * @return int
     */
    public static function int($val): int
    {
        return (int)$val;
    }

    /**
     * @param mixed $val
     *
     * @return bool
     */
    public static function bool($val): bool
    {
        return (bool)$val;
    }

    /**
     * @param mixed $val
     *
     * @return float
     */
    public static function float($val): float
    {
        return (float)$val;
    }

    /**
     * @param mixed $val
     *
     * @return string
     */
    public static function string($val): string
    {
        return (string)$val;
    }

    /**
     * @param mixed $val
     *
     * @return array
     */
    public static function array($val): array
    {
        return (array)$val;
    }

    /**
     * @param mixed $val
     *
     * @return object
     */
    public static function object($val)
    {
        return (object)$val;
    }
}
