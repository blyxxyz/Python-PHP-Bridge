<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer\Representer;

/**
 * Build Pythonish representations of objects.
 *
 * This class provides functionality similar to var_dump and friends, but
 * with a different, more terse style. These aren't to dump on a web page on
 * special occasions, but to routinely show in an interactive terminal
 * session to give feedback.
 *
 * Loosely following Python's conventions, a representation is either a
 * string of valid PHP code that evaluates to the same value, or a useful
 * description surrounded by < and >.
 */
class Representer implements RepresenterInterface
{
    /**
     * Represent any value.
     *
     * $depth can be used to specify how many levels deep the representation
     * may go.
     *
     * @param mixed $thing
     * @param int $depth
     * @return string
     */
    public static function repr($thing, int $depth = 2): string
    {
        $depth -= 1;

        if ($thing instanceof Representable) {
            return $thing->represent(static::class, $depth);
        }

        switch (gettype($thing)) {
            case 'resource':
                return static::reprResource($thing, $depth);
            case 'array':
                return static::reprArray($thing, $depth);
            case 'object':
                return static::reprObject($thing, $depth);
            default:
                return static::reprFallback($thing, $depth);
        }
    }

    /**
     * Represent a resource, including its type.
     *
     * @param resource $resource
     * @param int $depth
     * @return string
     */
    protected static function reprResource($resource, int $depth): string
    {
        $kind = get_resource_type($resource);
        $id = intval($resource);
        return "<$kind resource id #$id>";
    }

    /**
     * Represent an array using modern syntax, up to a certain depth.
     *
     * @param array $array
     * @param int $depth
     * @return string
     */
    protected static function reprArray(array $array, int $depth): string
    {
        if ($array === []) {
            return "[]";
        }
        if ($depth <= 0) {
            $count = count($array);
            return "[... ($count)]";
        }
        $content = [];
        if (self::arrayIsSequential($array)) {
            foreach ($array as $item) {
                $content[] = static::repr($item, $depth);
            }
        } else {
            foreach ($array as $key => $item) {
                $content[] = static::repr($key, $depth) . ' => '
                    . static::repr($item, $depth);
            }
        }
        return '[' . implode(', ', $content) . ']';
    }

    /**
     * Determine whether an array could have been created without using
     * associative syntax.
     *
     * @param array $array
     * @return bool
     */
    private static function arrayIsSequential(array $array): bool
    {
        if (count($array) === 0) {
            return true;
        }
        return array_keys($array) === range(0, count($array) - 1);
    }

    /**
     * Represent an object using its properties.
     *
     * @param object $object
     * @param int $depth
     * @return string
     */
    protected static function reprObject($object, int $depth): string
    {
        if ($depth <= 0) {
            return self::opaqueReprObject($object);
        }

        $cls = get_class($object);
        $properties = (array)$object;

        if (count($properties) === 0) {
            return self::opaqueReprObject($object);
        }

        $propertyReprs = [];
        foreach ($properties as $key => $value) {
            // private properties do something obscene with null bytes
            $keypieces = explode("\0", (string)$key);
            $key = $keypieces[count($keypieces) - 1];
            $propertyReprs[] = "$key=" . static::repr($value, $depth);
        }
        return "<$cls object (" . implode(', ', $propertyReprs) .")>";
    }

    /**
     * Represent an object using only its class and hash.
     *
     * @param object $object
     * @return string
     */
    protected static function opaqueReprObject($object): string
    {
        $cls = get_class($object);
        $hash = spl_object_hash($object);
        if (strlen($hash) === 32) {
            // Get the only interesting part
            $hash = substr($hash, 8, 8);
        }
        return "<$cls object 0x$hash>";
    }

    /**
     * Represent a value if no other handler is available.
     *
     * @param mixed $thing
     * @param int $depth
     *
     * @return string
     */
    protected static function reprFallback($thing, int $depth): string
    {
        if (is_null($thing) || is_bool($thing)) {
            return strtolower(var_export($thing, true));
        }

        if (is_int($thing) || is_float($thing) || is_string($thing)) {
            return var_export($thing, true);
        }

        // We don't know what this is so we won't risk var_export
        $type = gettype($thing);
        return "<$type>";
    }
}
