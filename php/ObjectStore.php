<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

/**
 * Stores objects and resources so they can be serialized
 */
class ObjectStore
{
    /** @var array<string|int, object|resource> */
    private $objects;

    public function __construct()
    {
        $this->objects = [];
    }

    /**
     * @param object|resource $object
     *
     * @return string|int
     */
    public function encode($object)
    {
        if (is_resource($object)) {
            // This uses an implementation detail, but it's the best we have
            $key = intval($object);
        } else {
            $key = spl_object_hash($object);
        }
        $this->objects[$key] = $object;
        return $key;
    }

    /**
     * @param string|int $key
     *
     * @return object|resource
     */
    public function decode($key)
    {
        return $this->objects[$key];
    }
}
