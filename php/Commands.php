<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

/**
 * Implements the commands called through the bridge
 */
class Commands
{
    /**
     * Get a constant by its name
     *
     * @param string $data
     *
     * @return mixed
     */
    public static function getConst(string $data)
    {
        if (!defined($data)) {
            throw new \Exception("Constant '$data' is not defined");
        }
        return constant($data);
    }

    /**
     * Call a function
     *
     * @param string $name
     * @param array $args
     *
     * @return mixed
     */
    public static function callFun(string $name, array $args)
    {
        if (is_callable($name)) {
            return $name(...$args);
        } elseif (method_exists(NonFunctionProxy::class, $name)) {
            return NonFunctionProxy::$name(...$args);
        }
        throw new \Exception("Could not resolve function '$name'");
    }

    /**
     * Instantiate an object
     *
     * @param string $name
     * @param array $args
     *
     * @return object
     */
    public static function createObject(string $name, array $args)
    {
        return new $name(...$args);
    }

    /**
     * Get an array of all defined constant names
     *
     * @return array
     */
    public static function listConsts(): array
    {
        return array_keys(get_defined_constants());
    }

    /**
     * Get an array of names of all defined functions
     *
     * @return array
     */
    public static function listFuns(): array
    {
        $result = get_class_methods(NonFunctionProxy::class);
        foreach (get_defined_functions() as $functions) {
            $result = array_merge($result, $functions);
        }
        return $result;
    }

    /**
     * Get an array of names of all declared classes
     *
     * @return array
     */
    public static function listClasses(): array
    {
        return get_declared_classes();
    }

    /**
     * Try to guess what a name represents
     *
     * @param string $name
     *
     * @return array
     */
    public static function resolveName(string $name)
    {
        if (defined($name)) {
            return ['const', constant($name)];
        } elseif (function_exists($name) ||
            method_exists(NonFunctionProxy::class, $name)) {
            return ['func', $name];
        } elseif (class_exists($name)) {
            return ['class', $name];
        }
        throw new \Exception("Could not resolve name '$name'");
    }

    /**
     * Get a string representation of a value, for Python's repr.
     *
     * var_export would be more correct than print_r, as it creates valid
     * PHP, but it's less readable and handles recursion badly. PHP doesn't
     * have a repr protocol.
     *
     * @param mixed $value
     *
     * @psalm-suppress InvalidReturnType
     * @return string
     */
    public static function repr($value): string
    {
        if (is_resource($value)) {
            $kind = get_resource_type($value);
            $id = intval($value);
            return "$kind resource id #$id";
        }
        /** @psalm-suppress InvalidReturnStatement */
        return print_r($value, true);
    }

    /**
     * Cast a value to a string.
     *
     * @param mixed $value
     *
     * @return string
     */
    public static function str($value): string
    {
        return (string)$value;
    }
}
