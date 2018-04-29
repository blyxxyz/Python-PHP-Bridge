<?php
/** @noinspection PhpVariableVariableInspection */
declare(strict_types=1);

namespace blyxxyz\PythonServer;

use blyxxyz\PythonServer\Exceptions\AttributeError;

/**
 * Implements the commands called through the bridge
 */
class Commands
{
    /**
     * Get a constant by its name.
     *
     * @param string $name
     *
     * @return mixed
     */
    public static function getConst(string $name)
    {
        if (!defined($name)) {
            throw new \Exception("Constant '$name' is not defined");
        }
        return constant($name);
    }

    /**
     * Define a constant.
     *
     * @param string $name
     * @param mixed $value
     *
     * @return null
     */
    public static function setConst(string $name, $value)
    {
        define($name, $value);
        return null;
    }

    /**
     * Get a global variable.
     *
     * @param string $name
     *
     * @return mixed
     */
    public static function getGlobal(string $name)
    {
        if (!array_key_exists($name, $GLOBALS)) {
            throw new \Exception("Global variable '$name' does not exist");
        }
        if ($name === 'GLOBALS') {
            // This doesn't work:
            // $value = $GLOBALS['GLOBALS'];
            // $value['GLOBALS'] = null;
            // It turns $GLOBALS into null. So we do it like this.
            $result = [];
            foreach ($GLOBALS as $key => $value) {
                if ($key !== 'GLOBALS') {
                    $result[$key] = $value;
                }
            }
            return $result;
        }
        return $GLOBALS[$name];
    }

    /**
     * Set a global variable.
     *
     * @param string $name
     * @param mixed $value
     *
     * @return null
     */
    public static function setGlobal(string $name, $value)
    {
        $GLOBALS[$name] = $value;
        return null;
    }

    /**
     * Call a function.
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
     * Call an object.
     *
     * @param callable $obj
     * @param array $args
     *
     * @return mixed
     */
    public static function callObj($obj, array $args)
    {
        return $obj(...$args);
    }

    /**
     * Call an object or class method.
     *
     * @param object|string $obj
     * @param string $name
     * @param array $args
     *
     * @return mixed
     */
    public static function callMethod($obj, string $name, array $args)
    {
        $method = [$obj, $name];
        return $method(...$args);
    }

    /**
     * Instantiate an object.
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
     * Check whether an offset exists.
     *
     * @param \ArrayAccess $obj
     * @param mixed $offset
     *
     * @return bool
     */
    public static function hasItem($obj, $offset): bool
    {
        return isset($obj[$offset]);
    }

    /**
     * Get the value at an offset.
     *
     * @param \ArrayAccess $obj
     * @param mixed $offset
     *
     * @return mixed
     */
    public static function getItem($obj, $offset)
    {
        return $obj[$offset];
    }

    /**
     * Set the value at an offset.
     *
     * @param \ArrayAccess $obj
     * @param mixed $offset
     * @param mixed $value
     *
     * @return null
     */
    public static function setItem($obj, $offset, $value)
    {
        $obj[$offset] = $value;
        return null;
    }

    /**
     * Remove the value at an offset.
     *
     * @param \ArrayAccess $obj
     * @param mixed $offset
     *
     * @return null
     */
    public static function delItem($obj, $offset)
    {
        unset($obj[$offset]);
        return null;
    }

    /**
     * Get an object property.
     *
     * @param object $obj
     * @param string $name
     *
     * @return mixed
     */
    public static function getProperty($obj, string $name)
    {
        if (isset($obj->$name)) {
            return $obj->$name;
        } else {
            $class = get_class($obj);
            throw new AttributeError(
                "'$class' object has no property '$name'"
            );
        }
    }

    /**
     * Set an object property to a value.
     *
     * @param object $obj
     * @param string $name
     * @param mixed $value
     *
     * @return null
     */
    public static function setProperty($obj, $name, $value)
    {
        /** @noinspection PhpVariableVariableInspection */
        $obj->$name = $value;
        return null;
    }

    /**
     * Get an array of all property names.
     *
     * Doesn't work for all objects. For example, properties set on an
     * ArrayObject don't show up. They don't show up either when the object
     * is cast to an array, so that's probably related.
     *
     * @param object $obj
     *
     * @return array
     */
    public static function listProperties($obj)
    {
        $properties = [];
        foreach ((new \ReflectionObject($obj))->getProperties() as $property) {
            if ($property->isPublic()) {
                $properties[] = $property->getName();
            }
        }
        return $properties;
    }

    /**
     * Get a summary of a class
     *
     * @param string $class
     *
     * @return array
     */
    public static function classInfo(string $class): array
    {
        $reflectionClass = new \ReflectionClass($class);
        $parent = $reflectionClass->getParentClass();
        if ($parent !== false) {
            $parent = $parent->getName();
        }
        $info = [
            'name' => $reflectionClass->getName(),
            'doc' => $reflectionClass->getDocComment(),
            'consts' => [],
            'methods' => [],
            'interfaces' => $reflectionClass->getInterfaceNames(),
            'isAbstract' => $reflectionClass->isAbstract(),
            'isInterface' => $reflectionClass->isInterface(),
            'parent' => $parent
        ];
        foreach ($reflectionClass->getReflectionConstants() as $constant) {
            if ($constant->isPublic()) {
                $info['consts'][$constant->getName()] = $constant->getValue();
            }
        }
        foreach ($reflectionClass->getMethods() as $method) {
            if ($method->isPublic()) {
                $info['methods'][$method->getName()] = [
                    'static' => $method->isStatic(),
                    'doc' => $method->getDocComment(),
                    'params' => array_map(
                        [static::class, 'paramInfo'],
                        $method->getParameters()
                    ),
                    'returnType' => static::typeInfo($method->getReturnType())
                ];
            }
        }
        return $info;
    }

    /**
     * Get detailed information about a function.
     *
     * @param string $name
     *
     * @return array
     */
    public static function funcInfo(string $name): array
    {
        if (is_callable($name) && is_string($name)) {
            $function = new \ReflectionFunction($name);
        } elseif (method_exists(NonFunctionProxy::class, $name)) {
            $function = (new \ReflectionClass(NonFunctionProxy::class))
                ->getMethod($name);
        } else {
            throw new \Exception("Could not resolve function '$name'");
        }
        return [
            'name' => $function->getName(),
            'doc' => $function->getDocComment(),
            'params' => array_map(
                [static::class, 'paramInfo'],
                $function->getParameters()
            ),
            'returnType' => static::typeInfo($function->getReturnType())
        ];
    }

    /**
     * Serialize information about a function parameter.
     *
     * @param \ReflectionParameter $parameter
     *
     * @return array
     */
    private static function paramInfo(\ReflectionParameter $parameter): array
    {
        $hasDefault = $parameter->isDefaultValueAvailable();
        return [
            'name' => $parameter->getName(),
            'type' => static::typeInfo($parameter->getType()),
            'hasDefault' => $hasDefault,
            'default' => $hasDefault ? $parameter->getDefaultValue() : null,
            'variadic' => $parameter->isVariadic()
        ];
    }

    /**
     * Serialize information about a parameter or return type.
     *
     * @param \ReflectionType|null $type
     *
     * @return array|null
     */
    private static function typeInfo(\ReflectionType $type = null)
    {
        if ($type === null) {
            return null;
        }
        return [
            'name' => $type->getName(),
            'isClass' => !$type->isBuiltin(),
            'nullable' => $type->allowsNull(),
        ];
    }

    /**
     * Get an array of all defined constant names.
     *
     * @return array
     */
    public static function listConsts(): array
    {
        return array_keys(get_defined_constants());
    }

    /**
     * Get an array of all global variable names.
     *
     * @return array
     */
    public static function listGlobals(): array
    {
        return array_keys($GLOBALS);
    }

    /**
     * Get an array of names of all defined functions.
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
     * Get an array of names of all declared classes.
     *
     * @return array
     */
    public static function listClasses(): array
    {
        return array_merge(get_declared_classes(), get_declared_interfaces());
    }

    /**
     * Try to guess what a name represents.
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
        } elseif (class_exists($name) || interface_exists($name)) {
            return ['class', $name];
        } elseif (array_key_exists($name, $GLOBALS)) {
            return ['global', static::getGlobal($name)];
        } else {
            return ['none', null];
        }
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

    /**
     * Get the count/length of an object.
     *
     * @param \Countable $value
     *
     * @return int
     */
    public static function count(\Countable $value): int
    {
        return count($value);
    }

    /**
     * Start iterating over something.
     *
     * We deliberately return the Generator object so we can get values out
     * of it in further commands.
     *
     * @param iterable $iterable
     *
     * @return \Generator
     */
    public static function startIteration($iterable): \Generator
    {
        /** @psalm-suppress RedundantConditionGivenDocblockType */
        if (!(is_array($iterable) || $iterable instanceof \Traversable)) {
            if (is_object($iterable)) {
                $class = get_class($iterable);
                throw new \TypeError("'$class' object is not iterable");
            }
            $type = gettype($iterable);
            throw new \TypeError("'$type' value is not iterable");
        }
        foreach ($iterable as $key => $value) {
            yield $key => $value;
        }
    }

    /**
     * Get the next key and value from a generator.
     *
     * Returns an array containing a bool indicating whether the generator is
     * still going, the new key, and the new value.
     *
     * @param \Generator $generator
     *
     * @return array
     */
    public static function nextIteration(\Generator $generator): array
    {
        $ret = [$generator->valid(), $generator->key(), $generator->current()];
        $generator->next();
        return $ret;
    }
}
