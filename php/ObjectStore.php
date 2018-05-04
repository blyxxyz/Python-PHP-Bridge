<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer;

/**
 * Stores objects and resources so they can be serialized
 */
class ObjectStore
{
    /** @var array<string, object> */
    private $objects;

    /** @var array<int, resource> */
    private $resources;

    public function __construct()
    {
        $this->objects = [];
        $this->resources = [];
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
            $this->resources[$key] = $object;
        } else {
            $key = spl_object_hash($object);
            $this->objects[$key] = $object;
        }
        return $key;
    }

    /**
     * @param string|int $key
     *
     * @return object|resource
     */
    public function decode($key)
    {
        if (is_int($key)) {
            return $this->resources[$key];
        } else {
            return $this->objects[$key];
        }
    }

    /**
     * @param string|int $key
     *
     * @return void
     */
    public function remove($key)
    {
        if (is_int($key)) {
            unset($this->resources[$key]);
        } else {
            unset($this->objects[$key]);
        }
    }
}
