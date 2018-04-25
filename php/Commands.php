<?php
declare(strict_types=1);

namespace PythonBridge;

/**
 * Implements the commands called through the bridge
 *
 * @package PythonBridge
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
        } elseif (is_callable([NonFunctionProxy::class, $name])) {
            return NonFunctionProxy::$name(...$args);
        }
        throw new \Exception("Could not resolve function '$name'");
    }

    /**
     * Get an array of all defined constant names
     *
     * @param string $prefix TODO
     *
     * @return array
     */
    public static function listConsts(string $prefix = ''): array
    {
        return array_keys(get_defined_constants());
    }

    public static function listFuns(string $prefix = ''): array
    {
        $result = [];
        foreach (get_defined_functions() as $functions) {
            $result = array_merge($result, $functions);
        }
        return $result;
    }
}
