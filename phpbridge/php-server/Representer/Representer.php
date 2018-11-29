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
     * Shorthand to get a representation without making an object manually.
     *
     * @param mixed $thing
     * @param int $depth
     * @return string
     */
    public static function r($thing, int $depth = 2): string
    {
        return (new static)->repr($thing, $depth);
    }

    const TRUE = 'true';
    const FALSE = 'false';
    const NULL = 'null';

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
    public function repr($thing, int $depth = 2): string
    {
        $depth -= 1;

        switch (gettype($thing)) {
            case 'resource':
                return $this->reprResource($thing, $depth);
            case 'array':
                return $this->reprArray($thing, $depth);
            case 'boolean':
                return $thing ? static::TRUE : static::FALSE;
            case 'NULL':
                return static::NULL;
            case 'double':
                return $this->reprFloat($thing, $depth);
            case 'string':
                return $this->reprString($thing, $depth);
            case 'object':
                return $this->reprObject($thing, $depth);
            default:
                return $this->reprFallback($thing, $depth);
        }
    }

    const RESOURCE_IDEN = 'resource';

    /**
     * Represent a resource, including its type.
     *
     * @param resource $resource
     * @param int $depth
     * @return string
     */
    protected function reprResource($resource, int $depth): string
    {
        $kind = get_resource_type($resource);
        $id = intval($resource);
        return "<$kind " . static::RESOURCE_IDEN . " id #$id>";
    }

    const SEQ_ARRAY_DELIMS = ['[', ']'];
    const ASSOC_ARRAY_DELIMS = ['[', ']'];
    const KEY_SEP = ' => ';
    const ITEM_SEP = ', ';

    /**
     * Represent an array using modern syntax, up to a certain depth.
     *
     * @param array $array
     * @param int $depth
     * @return string
     */
    protected function reprArray(array $array, int $depth): string
    {
        if ($array === []) {
            return implode(static::ASSOC_ARRAY_DELIMS);
        }
        $sequential = self::arrayIsSequential($array);
        if ($depth <= 0) {
            $count = count($array);
            if ($sequential) {
                return implode(
                    "... ($count)",
                    static::ASSOC_ARRAY_DELIMS
                );
            } else {
                return implode(
                    "..." . static::KEY_SEP . "($count)",
                    static::SEQ_ARRAY_DELIMS
                );
            }
        }
        $content = [];
        if (self::arrayIsSequential($array)) {
            foreach ($array as $item) {
                $content[] = $this->repr($item, $depth);
            }
            return implode(
                implode(static::ITEM_SEP, $content),
                static::SEQ_ARRAY_DELIMS
            );
        } else {
            foreach ($array as $key => $item) {
                $content[] = $this->repr($key, $depth) . static::KEY_SEP
                    . $this->repr($item, $depth);
            }
            return implode(
                implode(static::ITEM_SEP, $content),
                static::ASSOC_ARRAY_DELIMS
            );
        }
    }

    /**
     * Determine whether an array could have been created without using
     * associative syntax.
     *
     * @param array $array
     * @return bool
     */
    protected static function arrayIsSequential(array $array): bool
    {
        if (count($array) === 0) {
            return true;
        }
        return array_keys($array) === range(0, count($array) - 1);
    }

    const NAN = 'NAN';
    const INF = 'INF';
    const NEG_INF = '-INF';

    protected function reprFloat(float $thing, int $depth): string
    {
        if (is_nan($thing)) {
            return static::NAN;
        } elseif (is_infinite($thing) && $thing > 0) {
            return static::INF;
        } elseif (is_infinite($thing) && $thing < 0) {
            return static::NEG_INF;
        }
        return $this->reprFallback($thing, $depth);
    }

    protected function reprString(string $thing, int $depth): string
    {
        return $this->reprFallback($thing, $depth);
    }

    const OBJECT_IDEN = 'object';

    /**
     * Represent an object using its properties.
     *
     * @param object $object
     * @param int $depth
     * @return string
     */
    protected function reprObject($object, int $depth): string
    {
        if ($depth <= 0) {
            return $this->opaqueReprObject($object);
        }

        $cls = $this->convertClassName(get_class($object));
        $properties = (array)$object;

        if (count($properties) === 0) {
            return $this->opaqueReprObject($object);
        }

        $propertyReprs = [];
        foreach ($properties as $key => $value) {
            // private properties do something obscene with null bytes
            $keypieces = explode("\0", (string)$key);
            $key = $keypieces[count($keypieces) - 1];
            $propertyReprs[] = "$key=" . $this->repr($value, $depth);
        }
        return "<$cls " . static::OBJECT_IDEN .
            " (" . implode(', ', $propertyReprs) . ")>";
    }

    /**
     * Represent an object using only its class and hash.
     *
     * @param object $object
     * @return string
     */
    protected function opaqueReprObject($object): string
    {
        $cls = $this->convertClassName(get_class($object));
        $hash = spl_object_hash($object);
        if (strlen($hash) === 32) {
            // Get the only interesting part
            $hash = substr($hash, 8, 8);
        }
        return "<$cls " . static::OBJECT_IDEN . " 0x$hash>";
    }

    /**
     * Convert a class name to the preferred notation.
     *
     * @param string $name
     * @return string
     */
    protected function convertClassName(string $name): string
    {
        return $name;
    }

    /**
     * Represent a value if no other handler is available.
     *
     * @param mixed $thing
     * @param int $depth
     *
     * @return string
     */
    protected function reprFallback($thing, int $depth): string
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
