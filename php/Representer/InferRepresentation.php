<?php
declare(strict_types=1);

namespace blyxxyz\PythonServer\Representer;

/**
 * Implement Representable by inspecting the constructor.
 *
 * The arguments of the constructor must correspond to properties with the
 * same names. If they don't, implement Representable manually.
 */
trait InferRepresentation
{
    public function represent(
        string $callingClass = Representer::class,
        int $depth = 2
    ): string {
        $class = new \ReflectionClass(static::class);
        $constructor = $class->getConstructor();
        $args = [];
        foreach ($constructor->getParameters() as $arg) {
            $name = $arg->getName();
            $args[] = $callingClass::repr($this->$name);
        }
        $argList = implode(', ', $args);
        return static::class . "($argList)";
    }
}
